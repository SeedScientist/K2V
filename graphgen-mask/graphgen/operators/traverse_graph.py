import asyncio
import gradio as gr
import random
import re

from tqdm.asyncio import tqdm as tqdm_async

from graphgen.models import OpenAIModel, NetworkXStorage, TraverseStrategy, Tokenizer, JsonKVStorage
from graphgen.templates import ANSWER_REPHRASING_PROMPT, QUESTION_GENERATION_PROMPT, MULTI_HOP_GENERATION_PROMPT
from graphgen.utils import detect_main_language, compute_content_hash, logger
from graphgen.operators.split_graph import get_batches_with_strategy

random.seed(42)

async def _pre_tokenize(graph_storage: NetworkXStorage,
                        tokenizer: Tokenizer,
                        edges: list,
                        nodes: list) -> tuple:

    sem = asyncio.Semaphore(1000)
    async def handle_edge(edge: tuple) -> tuple:
        async with sem:
            if 'length' not in edge[2]:
                edge[2]['length'] = len(
                    await asyncio.get_event_loop().run_in_executor(None,
                                                                   tokenizer.encode_string,
                                                                   edge[2]['description']))
            return edge

    async def handle_node(node: dict) -> dict:
        async with sem:
            if 'length' not in node[1]:
                node[1]['length'] = len(
                    await asyncio.get_event_loop().run_in_executor(None,
                                                                   tokenizer.encode_string,
                                                                   node[1]['description']))
            return node

    new_edges = []
    new_nodes = []

    for result in tqdm_async(asyncio.as_completed([handle_edge(edge) for edge in edges]),
                             total=len(edges), desc="Pre-tokenizing edges"):
        new_edge = await result
        await graph_storage.update_edge(new_edge[0], new_edge[1], new_edge[2])
        new_edges.append(new_edge)

    for result in tqdm_async(asyncio.as_completed([handle_node(node) for node in nodes]),
                             total=len(nodes), desc="Pre-tokenizing nodes"):
        new_node = await result
        await graph_storage.update_node(new_node[0], new_node[1])
        new_nodes.append(new_node)

    await graph_storage.index_done_callback()
    return new_edges, new_nodes

async def _construct_rephrasing_prompt(_process_nodes: list,
                                       _process_edges: list,
                                       text_chunks_storage: JsonKVStorage,
                                       add_context: bool = False
                                       ) -> str:
    entities = [
        f"{_process_node['node_id']}: {_process_node['description']}" for _process_node in _process_nodes
    ]
    relations = [
        f"{_process_edge[0]} -- {_process_edge[1]}: {_process_edge[2]['description']}"
        for _process_edge in _process_edges
    ]

    entities_str = "\n".join([f"{index + 1}. {entity}" for index, entity in enumerate(entities)])
    relations_str = "\n".join([f"{index + 1}. {relation}" for index, relation in enumerate(relations)])
    language = "Chinese" if detect_main_language(entities_str + relations_str) == "zh" else "English"

    if add_context:
        original_ids = ([node['source_id'].split('<SEP>')[0] for node in _process_nodes] +
                        [edge[2]['source_id'].split('<SEP>')[0] for edge in _process_edges])

        original_ids = list(set(original_ids))
        original_text = await text_chunks_storage.get_by_ids(original_ids)
        original_text = "\n".join([f"{index + 1}. {text['content']}" for index, text in enumerate(original_text)])

        prompt = ANSWER_REPHRASING_PROMPT[language]['CONTEXT_TEMPLATE'].format(
            language=language,
            original_text=original_text,
            entities=entities_str,
            relationships=relations_str
        )
        return prompt

    prompt = ANSWER_REPHRASING_PROMPT[language]['TEMPLATE'].format(
        language=language,
        entities=entities_str,
        relationships=relations_str
    )
    return prompt

def get_loss_tercile(losses: list) -> (float, float):
    losses = sorted(losses)
    q1_index = int(len(losses) * (1 / 3))
    q2_index = int(len(losses) * (2 / 3))

    return losses[q1_index], losses[q2_index]

def get_average_loss(batch: tuple, loss_strategy: str) -> float:
    if loss_strategy == "only_edge":
        return sum(edge[2]['loss'] for edge in batch[1]) / len(batch[1])
    if loss_strategy == "both":
        return sum(edge[2]['loss'] for edge in batch[1]) + sum(node['loss'] for node in batch[0]) / \
               (len(batch[0]) + len(batch[1]))
    raise ValueError("Invalid loss strategy")

def _post_process_synthetic_data(data):
    block = data.split("\n\n")
    qas = []
    for line in block:
        if "Question:" in line and "Answer:" in line:
            question = line.split("Question:")[1].split("Answer:")[0].strip()
            answer = line.split("Answer:")[1].strip()
            qas.append({
                "question": question,
                "answer": answer
            })
        elif "问题：" in line and "答案：" in line:
            question = line.split("问题：")[1].split("答案：")[0].strip()
            answer = line.split("答案：")[1].strip()
            qas.append({
                "question": question,
                "answer": answer
            })
        elif "问题:" in line and "回答:" in line:
            question = line.split("问题:")[1].split("回答:")[0].strip()
            answer = line.split("回答:")[1].strip()
            qas.append({
                "question": question,
                "answer": answer
            })
    return qas

async def traverse_graph_by_edge(
    llm_client: OpenAIModel,
    tokenizer: Tokenizer,
    graph_storage: NetworkXStorage,
    traverse_strategy: TraverseStrategy,
    text_chunks_storage: JsonKVStorage,
    progress_bar: gr.Progress = None,
    max_concurrent: int = 1000,
    is_fill_blank: bool = None
) -> dict:
    """
    Traverse the graph

    :param llm_client
    :param tokenizer
    :param graph_storage
    :param traverse_strategy
    :param text_chunks_storage
    :param progress_bar
    :param max_concurrent
    :return: question and answer
    """

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _process_nodes_and_edges(
            _process_nodes: list,
            _process_edges: list,
    ) -> str:
        prompt = await _construct_rephrasing_prompt(
            _process_nodes,
            _process_edges,
            text_chunks_storage,
            add_context = False
        )
        context = await llm_client.generate_answer(prompt)

        # post-process the context
        if context.startswith("Rephrased Text:"):
            context = context[len("Rephrased Text:"):].strip()
        elif context.startswith("重述文本:"):
            context = context[len("重述文本:"):].strip()

        return context

    async def _process_single_batch(
        _process_batch: tuple,
        is_fill_blank: bool,
    ) -> dict:
        async with semaphore:
            context = await _process_nodes_and_edges(
                _process_batch[0],
                _process_batch[1],
            )

            language = "Chinese" if detect_main_language(context) == "zh" else "English"
            pre_length = sum(node['length'] for node in _process_batch[0]) \
                         + sum(edge[2]['length'] for edge in _process_batch[1])

            # 生成填空题
            if is_fill_blank and _process_batch[0]: 
                # 随机选择一个节点进行mask
                masked_node = random.choice(_process_batch[0])
                masked_entity = masked_node.get('node_id', '').strip('"')

                # 获取第一层邻接节点
                first_layer_nodes = await graph_storage.neighbors(masked_node['node_id'])
                # 过滤掉出现在context中的节点，但是保留所有节点用于后续的BFS
                first_layer_filtered = []
                first_layer_all = list(first_layer_nodes)
                for node in first_layer_all:
                    node_stripped = node.strip('"')
                    match_pattern = re.compile(re.escape(node_stripped), re.IGNORECASE)
                    if not match_pattern.search(context):
                        first_layer_filtered.append(node_stripped)
                
                adjacent_nodes = {"1": first_layer_filtered}    # {layer_number: [node_ids]}
                
                # 如果第一层过滤后的邻接节点数量不足4个，继续获取更多层的邻接节点
                total_filtered_nodes = len(first_layer_filtered)
                if total_filtered_nodes < 4:
                    visited = set(first_layer_all)  # Use all nodes for visited set to avoid duplicates
                    visited.add(masked_node['node_id'])
                    queue = [(node_id, 1) for node_id in first_layer_all]  # Use all nodes for BFS
                    
                    while queue and total_filtered_nodes < 4:
                        current_id, current_layer = queue.pop(0)
    
                        neighbors = await graph_storage.neighbors(current_id)
                        next_layer = current_layer + 1
                        next_layer_str = str(next_layer)
                        
                        if next_layer_str not in adjacent_nodes:
                            adjacent_nodes[next_layer_str] = []
                        
                        for neighbor in neighbors:
                            if neighbor not in visited:
                                visited.add(neighbor)
                                # 过滤掉出现在context中的节点
                                neighbor_stripped = neighbor.strip('"')
                                match_pattern = re.compile(re.escape(neighbor_stripped), re.IGNORECASE)
                                if not match_pattern.search(context):
                                    adjacent_nodes[next_layer_str].append(neighbor_stripped)
                                    total_filtered_nodes += 1
                                # 把所有节点都加入队列，用于后续的BFS
                                queue.append((neighbor, next_layer))
                                
                # 创建填空版本的上下文
                if masked_entity:
                    masked_entity_pattern = re.compile(re.escape(masked_entity), re.IGNORECASE)
                    if masked_entity_pattern.search(context):
                        masked_context = masked_entity_pattern.sub("{ }", context) 
                        # 为准确性，从实际上下文中提取替换的实际实体(保留原始大小写)
                        actual_entity = re.search(masked_entity_pattern, context).group(0)         
                        
                        logger.info("%d nodes and %d edges processed", len(_process_batch[0]), len(_process_batch[1]))
                        logger.info("Pre-length: %s", pre_length)
                        logger.info("Fill-in-blank Question: %s", masked_context)
                        logger.info("Answer: %s", actual_entity)
                        logger.info("Masked node adjacent nodes: %s", adjacent_nodes)
                        return {
                            compute_content_hash(masked_context): {
                                "question": masked_context,
                                "answer": actual_entity, 
                                "type": "fill_blank",
                                "adjacent_nodes": adjacent_nodes  
                            }
                        }
                else:
                    raise ValueError("Masked entity is not found")
            # # 如果不生成填空题，则生成单题
            # else:
            #     question = await llm_client.generate_answer(
            #         QUESTION_GENERATION_PROMPT[language]['SINGLE_TEMPLATE'].format(
            #             answer=context
            #         )
            #     )
            #     if question.startswith("Question:"):
            #         question = question[len("Question:"):].strip()
            #     elif question.startswith("问题："):
            #         question = question[len("问题："):].strip()

            #     logger.info("%d nodes and %d edges processed", len(_process_batch[0]), len(_process_batch[1]))
            #     logger.info("Pre-length: %s", pre_length)
            #     logger.info("Question: %s", question)
            #     logger.info("Answer: %s", context)

            #     return {
            #         compute_content_hash(context): {
            #             "question": question,
            #             "answer": context,
            #             "type": "qa",
            #             "loss": get_average_loss(_process_batch, traverse_strategy.loss_strategy)
            #         }
            #     }

            # # 原有的多题生成逻辑保持不变
            # if question_type == "multi":
            #     content = await llm_client.generate_answer(
            #         QUESTION_GENERATION_PROMPT[language]['MULTI_TEMPLATE'].format(
            #             doc=context
            #         )
            #     )
            #     qas = _post_process_synthetic_data(content)

            #     if len(qas) == 0:
            #         print(content)
            #         logger.error("Error occurred while processing batch, question or answer is None")
            #         return {}

            #     final_results = {}
            #     logger.info("%d nodes and %d edges processed", len(_process_batch[0]), len(_process_batch[1]))
            #     logger.info("Pre-length: %s", pre_length)
            #     for qa in qas:
            #         logger.info("Question: %s", qa['question'])
            #         logger.info("Answer: %s", qa['answer'])
            #         final_results[compute_content_hash(qa['question'])] = {
            #             "question": qa['question'],
            #             "answer": qa['answer'],
            #             "type": "qa",
            #             "loss": get_average_loss(_process_batch, traverse_strategy.loss_strategy)
            #         }
            #     return final_results

    results = {}
    edges = list(await graph_storage.get_all_edges())
    nodes = list(await graph_storage.get_all_nodes())

    edges, nodes = await _pre_tokenize(graph_storage, tokenizer, edges, nodes)

    processing_batches = await get_batches_with_strategy(
        nodes,
        edges,
        graph_storage,
        traverse_strategy
    )

    for result in tqdm_async(asyncio.as_completed(
        [_process_single_batch(batch, is_fill_blank) for batch in processing_batches]
    ), total=len(processing_batches), desc="[4/4]Generating QAs"):
        try:
            if progress_bar is not None:
                progress_bar(len(results) / len(processing_batches), desc="[4/4]Generating QAs")
            results.update(await result)
            if progress_bar is not None and len(results) == len(processing_batches):
                progress_bar(1, desc="[4/4]Generating QAs")
        except Exception as e: # pylint: disable=broad-except
            import traceback
            logger.error("Error occurred while generating QA: %s\n%s", e, traceback.format_exc())

    return results


async def traverse_graph_atomically(
    llm_client: OpenAIModel,
    tokenizer: Tokenizer,
    graph_storage: NetworkXStorage,
    traverse_strategy: TraverseStrategy,
    text_chunks_storage: JsonKVStorage,
    progress_bar: gr.Progress = None,
    max_concurrent: int = 1000
) -> dict:
    """
    Traverse the graph atomicly

    :param llm_client
    :param tokenizer
    :param graph_storage
    :param traverse_strategy
    :param text_chunks_storage
    :param progress_bar
    :param max_concurrent
    :return: question and answer
    """
    assert traverse_strategy.qa_form == "atomic"

    semaphore = asyncio.Semaphore(max_concurrent)
    async def _generate_question(
        node_or_edge: tuple
    ):
        if len(node_or_edge) == 2:
            des = node_or_edge[0] + ": " + node_or_edge[1]['description']
            loss = node_or_edge[1]['loss']
        else:
            des = node_or_edge[2]['description']
            loss = node_or_edge[2]['loss']

        async with semaphore:
            try:
                language = "Chinese" if detect_main_language(des) == "zh" else "English"

                qa = await llm_client.generate_answer(
                    QUESTION_GENERATION_PROMPT[language]['SINGLE_QA_TEMPLATE'].format(
                        doc=des
                    )
                )

                if "Question:" in qa and "Answer:" in qa:
                    question = qa.split("Question:")[1].split("Answer:")[0].strip()
                    answer = qa.split("Answer:")[1].strip()
                elif "问题：" in qa and "答案：" in qa:
                    question = qa.split("问题：")[1].split("答案：")[0].strip()
                    answer = qa.split("答案：")[1].strip()
                else:
                    return {}

                question = question.strip("\"")
                answer = answer.strip("\"")

                logger.info("Question: %s", question)
                logger.info("Answer: %s", answer)
                return {
                    compute_content_hash(question): {
                        "question": question,
                        "answer": answer,
                        "loss": loss
                    }
                }
            except Exception as e: # pylint: disable=broad-except
                logger.error("Error occurred while generating question: %s", e)
                return {}

    results = {}
    edges = list(await graph_storage.get_all_edges())
    nodes = list(await graph_storage.get_all_nodes())

    edges, nodes = await _pre_tokenize(graph_storage, tokenizer, edges, nodes)

    tasks = []
    for node in nodes:
        if "<SEP>" in node[1]['description']:
            description_list = node[1]['description'].split("<SEP>")
            for item in description_list:
                tasks.append((node[0], {"description": item, 'loss': node[1]['loss']}))
        else:
            tasks.append((node[0], node[1]))
    for edge in edges:
        if "<SEP>" in edge[2]['description']:
            description_list = edge[2]['description'].split("<SEP>")
            for item in description_list:
                tasks.append((edge[0], edge[1], {"description": item, 'loss': edge[2]['loss']}))
        else:
            tasks.append((edge[0], edge[1], edge[2]))

    for result in tqdm_async(
        asyncio.as_completed([_generate_question(task) for task in tasks]),
        total=len(tasks),
        desc="[4/4]Generating QAs"
    ):
        try:
            if progress_bar is not None:
                progress_bar(len(results) / len(tasks), desc="[4/4]Generating QAs")
            results.update(await result)
            if progress_bar is not None and len(results) == len(tasks):
                progress_bar(1, desc="[4/4]Generating QAs")
        except Exception as e: # pylint: disable=broad-except
            import traceback
            logger.error("Error occurred while generating QA: %s\n%s", e, traceback.format_exc())
    return results

async def traverse_graph_for_multi_hop(
    llm_client: OpenAIModel,
    tokenizer: Tokenizer,
    graph_storage: NetworkXStorage,
    traverse_strategy: TraverseStrategy,
    text_chunks_storage: JsonKVStorage,
    progress_bar: gr.Progress = None,
    max_concurrent: int = 1000
) -> dict:
    """
    Traverse the graph for multi-hop

    :param llm_client
    :param tokenizer
    :param graph_storage
    :param traverse_strategy
    :param text_chunks_storage
    :param progress_bar
    :param max_concurrent
    :return: question and answer
    """
    assert traverse_strategy.qa_form == "multi_hop"

    semaphore = asyncio.Semaphore(max_concurrent)

    results = {}
    edges = list(await graph_storage.get_all_edges())
    nodes = list(await graph_storage.get_all_nodes())

    edges, nodes = await _pre_tokenize(graph_storage, tokenizer, edges, nodes)

    processing_batches = await get_batches_with_strategy(
        nodes,
        edges,
        graph_storage,
        traverse_strategy
    )

    async def _process_single_batch(
        _process_batch: tuple
    ) -> dict:
        async with semaphore:
            try:
                language = "Chinese" if detect_main_language(_process_batch[0][0]['description']) == "zh" else "English"

                _process_nodes = _process_batch[0]
                _process_edges = _process_batch[1]

                entities = [
                    f"{_process_node['node_id']}: {_process_node['description']}" for _process_node in _process_nodes
                ]

                relations = [
                    f"{_process_edge[0]} -- {_process_edge[1]}: {_process_edge[2]['description']}"
                    for _process_edge in _process_edges
                ]

                entities_str = "\n".join([f"{index + 1}. {entity}" for index, entity in enumerate(entities)])
                relations_str = "\n".join([f"{index + 1}. {relation}" for index, relation in enumerate(relations)])

                prompt = MULTI_HOP_GENERATION_PROMPT[language].format(
                    entities=entities_str,
                    relationships=relations_str
                )

                context = await llm_client.generate_answer(prompt)

                # post-process the context
                if "Question:" in context and "Answer:" in context:
                    question = context.split("Question:")[1].split("Answer:")[0].strip()
                    answer = context.split("Answer:")[1].strip()
                elif "问题：" in context and "答案：" in context:
                    question = context.split("问题：")[1].split("答案：")[0].strip()
                    answer = context.split("答案：")[1].strip()
                else:
                    return {}

                question = question.strip("\"")
                answer = answer.strip("\"")

                logger.info("Question: %s", question)
                logger.info("Answer: %s", answer)

                return {
                    compute_content_hash(question): {
                        "question": question,
                        "answer": answer,
                        "loss": get_average_loss(_process_batch, traverse_strategy.loss_strategy),
                    }
                }

            except Exception as e: # pylint: disable=broad-except
                logger.error("Error occurred while processing batch: %s", e)
                return {}

    async for result in tqdm_async(
        asyncio.as_completed([_process_single_batch(batch) for batch in processing_batches]),
        total=len(processing_batches),
        desc="[4/4]Generating QAs"
    ):
        try:
            if progress_bar is not None:
                progress_bar(len(results) / len(processing_batches), desc="[4/4]Generating QAs")
            results.update(await result)
            if progress_bar is not None and len(results) == len(processing_batches):
                progress_bar(1, desc="[4/4]Generating QAs")
        except Exception as e: # pylint: disable=broad-except
            import traceback
            logger.error("Error occurred while generating QA: %s\n%s", e, traceback.format_exc())
    return results
