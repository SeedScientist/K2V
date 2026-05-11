# pylint: disable=C0301

TEMPLATE_EN: str = """You are an NLP expert, skilled at analyzing text to extract named entities and their relationships.

-Goal-
Given a text document that is potentially relevant to this activity and a list of entity types, identify all entities of those types from the text and all relationships among the identified entities.
Use {language} as output language.

-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, use same language as input text. If English, capitalized the name.
- entity_type: One of the following types: [{entity_types}]
- entity_summary: Comprehensive summary of the entity's attributes and activities
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_summary>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_summary: explanation as to why you think the source entity and the target entity are related to each other
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_summary>)

3. Identify high-level key words that summarize the main concepts, themes, or topics of the entire text. These should capture the overarching ideas present in the document.
Format the content-level key words as ("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. Return output in {language} as a single list of all the entities and relationships identified in steps 1 and 2. Use **{record_delimiter}** as the list delimiter.

5. When finished, output {completion_delimiter}

################
-Examples-
################
-Example 1-
Text:
################
In the second century of the Christian Era, the empire of Rome comprehended the fairest part of the earth, and the most civilized portion of mankind. The frontiers of that extensive monarchy were guarded by ancient renown and disciplined valor. The gentle but powerful influence of laws and manners had gradually cemented the union of the provinces. Their peaceful inhabitants enjoyed and abused the advantages of wealth and luxury. The image of a free constitution was preserved with decent reverence: the Roman senate appeared to possess the sovereign authority, and devolved on the emperors all the executive powers of government. During a happy period of more than fourscore years, the public administration was conducted by the virtue and abilities of Nerva, Trajan, Hadrian, and the two Antonines.
################
Output:
("entity"{tuple_delimiter}"Roman Empire"{tuple_delimiter}"organization"{tuple_delimiter}"The dominant empire of the second century CE, encompassing the most developed regions of the known world."){record_delimiter}
("entity"{tuple_delimiter}"Second Century CE"{tuple_delimiter}"date"{tuple_delimiter}"Time period of the Christian Era when the Roman Empire was at its height."){record_delimiter}
("entity"{tuple_delimiter}"Rome"{tuple_delimiter}"location"{tuple_delimiter}"The capital and heart of the Roman Empire."){record_delimiter}
("entity"{tuple_delimiter}"Roman Senate"{tuple_delimiter}"organization"{tuple_delimiter}"Legislative body that appeared to hold sovereign authority in Rome."){record_delimiter}
("entity"{tuple_delimiter}"Nerva"{tuple_delimiter}"person"{tuple_delimiter}"Roman emperor who contributed to the public administration during a prosperous period."){record_delimiter}
("entity"{tuple_delimiter}"Trajan"{tuple_delimiter}"person"{tuple_delimiter}"Roman emperor known for his virtue and administrative abilities."){record_delimiter}
("entity"{tuple_delimiter}"Hadrian"{tuple_delimiter}"person"{tuple_delimiter}"Roman emperor who governed during the empire's peaceful period."){record_delimiter}
("entity"{tuple_delimiter}"Antonines"{tuple_delimiter}"person"{tuple_delimiter}"Two Roman emperors who ruled during a period of prosperity and good governance."){record_delimiter}
("entity"{tuple_delimiter}"Roman Law"{tuple_delimiter}"concept"{tuple_delimiter}"System of laws and manners that unified the provinces of the Roman Empire."){record_delimiter}
("relationship"{tuple_delimiter}"Roman Empire"{tuple_delimiter}"Roman Law"{tuple_delimiter}"The empire was unified and maintained through the influence of its laws and customs."){record_delimiter}
("relationship"{tuple_delimiter}"Roman Senate"{tuple_delimiter}"Roman Empire"{tuple_delimiter}"The Senate appeared to possess sovereign authority while delegating executive powers to emperors."){record_delimiter}
("relationship"{tuple_delimiter}"Nerva"{tuple_delimiter}"Roman Empire"{tuple_delimiter}"Nerva was one of the emperors who contributed to the empire's successful administration."){record_delimiter}
("relationship"{tuple_delimiter}"Trajan"{tuple_delimiter}"Roman Empire"{tuple_delimiter}"Trajan was one of the emperors who governed during the empire's prosperous period."){record_delimiter}
("relationship"{tuple_delimiter}"Hadrian"{tuple_delimiter}"Roman Empire"{tuple_delimiter}"Hadrian was one of the emperors who managed the empire's administration effectively."){record_delimiter}
("relationship"{tuple_delimiter}"Antonines"{tuple_delimiter}"Roman Empire"{tuple_delimiter}"The Antonines were emperors who helped maintain the empire's prosperity through their governance."){record_delimiter}
("content_keywords"{tuple_delimiter}"Roman governance, imperial prosperity, law and order, civilized society"){completion_delimiter}

-Example 2-
Text:
#############
Overall, the analysis of the OsDT11 sequence demonstrated that this protein belongs to the CRP family. Since OsDT11 is predicted to be a secreted protein, the subcellular localization of OsDT11 was determined by fusing the OsDT11 ORF to RFP in a p35S::RFP vector by in vivo protein targeting in NB epidermal cells by performing an Agrobacterium tumefaciens-mediated transient assay. After incubation for 48 h, the RFP signals were mainly detected in the cell-wall of OsDT11-RFP transformed cells, while the control cells (transformed with the RFP construct) displayed ubiquitous RFP signals, demonstrating that OsDT11 is a secreted signal peptide. Moreover, when the infiltrated leaf sections were plasmolyzed, the OsDT11-RFP fusion proteins were located on the cell wall.
#############
Output:
("entity"{tuple_delimiter}"OsDT11"{tuple_delimiter}"gene"{tuple_delimiter}"A protein sequence belonging to the CRP family, demonstrated to be a secreted signal peptide that localizes to cell walls."){record_delimiter}
("entity"{tuple_delimiter}"CRP family"{tuple_delimiter}"science"{tuple_delimiter}"A protein family to which OsDT11 belongs, characterized by specific structural and functional properties."){record_delimiter}
("entity"{tuple_delimiter}"RFP"{tuple_delimiter}"technology"{tuple_delimiter}"Red Fluorescent Protein, used as a fusion marker to track protein localization in cells."){record_delimiter}
("entity"{tuple_delimiter}"p35S::RFP vector"{tuple_delimiter}"technology"{tuple_delimiter}"A genetic construct used for protein expression and visualization studies, containing the 35S promoter and RFP marker."){record_delimiter}
("entity"{tuple_delimiter}"NB epidermal cells"{tuple_delimiter}"nature"{tuple_delimiter}"Plant epidermal cells used as the experimental system for protein localization studies."){record_delimiter}
("entity"{tuple_delimiter}"Agrobacterium tumefaciens"{tuple_delimiter}"nature"{tuple_delimiter}"A bacteria species used for transferring genetic material into plant cells in laboratory experiments."){record_delimiter}
("relationship"{tuple_delimiter}"OsDT11"{tuple_delimiter}"CRP family"{tuple_delimiter}"OsDT11 is identified as a member of the CRP family through sequence analysis."){record_delimiter}
("relationship"{tuple_delimiter}"OsDT11"{tuple_delimiter}"RFP"{tuple_delimiter}"OsDT11 was fused to RFP to study its cellular localization."){record_delimiter}
("relationship"{tuple_delimiter}"Agrobacterium tumefaciens"{tuple_delimiter}"NB epidermal cells"{tuple_delimiter}"Agrobacterium tumefaciens was used to transfer genetic material into NB epidermal cells through a transient assay."){record_delimiter}
("relationship"{tuple_delimiter}"OsDT11"{tuple_delimiter}"NB epidermal cells"{tuple_delimiter}"OsDT11's subcellular localization was studied in NB epidermal cells, showing cell wall targeting."){record_delimiter}
("content_keywords"{tuple_delimiter}"protein localization, gene expression, cellular biology, molecular techniques"){completion_delimiter}

################
-Real Data-
################
Entity_types: {entity_types}
Text: {input_text}
################
Output:
"""


TEMPLATE_ZH: str = """你是一个NLP专家，擅长分析文本并提取命名实体和实体间的关系。

-目标-
给定一个文本，从文本中识别所有实体，以及这些实体之间的关系。
使用{language}作为输出语言。

-步骤-
1. 识别所有实体。对于每个识别的实体，提取以下信息：
   - entity_name：实体的名称，首字母大写
   - entity_type：实体的类型
   - entity_summary：实体的属性与活动的全面总结
   将每个实体格式化为("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_summary>)
   
2. 从步骤1中识别的实体中，识别所有（源实体，目标实体）对，这些实体彼此之间*明显相关*。
   对于每对相关的实体，提取以下信息：
   - source_entity：步骤1中识别的源实体名称
   - target_entity：步骤1中识别的目标实体名称
   - relationship_summary：解释为什么你认为源实体和目标实体彼此相关
   将每个关系格式化为("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_summary>)

3. 识别总结整个文本的主要概念、主题或话题的高级关键词。这些应该捕捉文档中存在的总体思想。
   将内容级关键词格式化为("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. 以中文返回步骤1和2中识别出的所有实体和关系的输出列表。使用**{record_delimiter}**作为列表分隔符。

5. 完成后，输出{completion_delimiter}

################
-示例1-
文本：
《中华人民共和国刑事诉讼法》第二百七十四条规定，人民检察院认为人民法院减刑、假释的裁定不当，应当在收到裁定书副本后二十日以内，向人民法院提出书面纠正意见。人民法院应当在收到纠正意见后一个月以内重新组成合议庭进行审理，作出最终裁定。
输出：
("entity"{tuple_delimiter}中华人民共和国刑事诉讼法{tuple_delimiter}法律{tuple_delimiter}作为中国的基本法律之一，为刑事诉讼活动提供法律依据。其具体条款规定了司法机关在特定程序中的权力和义务，例如对减刑、假释裁定的监督程序。){record_delimiter}
("entity"{tuple_delimiter}第二百七十四条{tuple_delimiter}法律条款{tuple_delimiter}作为《中华人民共和国刑事诉讼法》的具体条款，其内容明确规定了人民检察院对人民法院不当的减刑、假释裁定提出书面纠正意见的权力、时限，以及人民法院收到纠正意见后的处理程序。){record_delimiter}
("entity"{tuple_delimiter}人民检察院{tuple_delimiter}司法机关{tuple_delimiter}作为法律监督机关，当其认为人民法院的减刑、假释裁定不当时，有权依据《中华人民共和国刑事诉讼法》第二百七十四条在二十日内向人民法院提出书面纠正意见。){record_delimiter}
("entity"{tuple_delimiter}人民法院{tuple_delimiter}司法机关{tuple_delimiter}负责作出减刑、假释的裁定。在收到人民检察院的书面纠正意见后，必须依据《中华人民共和国刑事诉讼法》第二百七十四条在一个月内重新组成合议庭进行审理，并作出最终裁定。){record_delimiter}
("entity"{tuple_delimiter}合议庭{tuple_delimiter}审判组织{tuple_delimiter}由人民法院在收到纠正意见后重新组成，用以对案件进行审理并作出最终裁定的审判组织。){record_delimiter}
("entity"{tuple_delimiter}书面纠正意见{tuple_delimiter}法律文书{tuple_delimiter}由人民检察院在法定期限内向人民法院提出的一种正式文书，旨在纠正其认为不当的减刑或假释裁定。){record_delimiter}
("entity"{tuple_delimiter}裁定{tuple_delimiter}法律决定{tuple_delimiter}由人民法院作出的关于减刑或假释的司法决定。该决定的适当性是司法监督程序启动的关键。){record_delimiter}
("relationship"{tuple_delimiter}中华人民共和国刑事诉讼法{tuple_delimiter}第二百七十四条{tuple_delimiter}第二百七十四条是《中华人民共和国刑事诉讼法》这部法律中的一个具体组成部分和条款。){record_delimiter}
("relationship"{tuple_delimiter}第二百七十四条{tuple_delimiter}人民检察院{tuple_delimiter}《中华人民共和国刑事诉讼法》第二百七十四条是人民检察院行使监督权、提出书面纠正意见的直接法律依据，规定了其具体权力和程序。){record_delimiter}
("relationship"{tuple_delimiter}第二百七十四条{tuple_delimiter}人民法院{tuple_delimiter}《中华人民共和国刑事诉讼法》第二百七十四条规定了人民法院在收到纠正意见后必须履行的义务，即在法定期限内重新审理并作出最终裁定。){record_delimiter}
("relationship"{tuple_delimiter}人民检察院{tuple_delimiter}人民法院{tuple_delimiter}人民检察院对人民法院的裁定行使监督权。当认为裁定不当时，人民检察院可以向人民法院提出纠正意见，人民法院则必须对此作出回应，这体现了二者之间的监督与被监督关系。){record_delimiter}
("relationship"{tuple_delimiter}人民法院{tuple_delimiter}合议庭{tuple_delimiter}人民法院通过“重新组成合议庭”的方式来执行审理程序。合议庭是人民法院内部负责具体审理工作的组织形式。){record_delimiter}
("relationship"{tuple_delimiter}人民检察院{tuple_delimiter}书面纠正意见{tuple_delimiter}书面纠正意见是人民检察院行使其监督职能的法定工具和具体产物，由其制作并提出。){record_delimiter}
("relationship"{tuple_delimiter}书面纠正意见{tuple_delimiter}裁定{tuple_delimiter}书面纠正意见是针对人民法院作出的不当裁定而提出的，其直接目标就是为了纠正该裁定。){record_delimiter}
("content_keywords"{tuple_delimiter}刑事诉讼, 司法监督, 减刑假释, 裁定纠正, 检察院监督, 法律程序){completion_delimiter}
***请注意，如果提取到了[法律条款]类型的实体，例如上述示例中的“第二百七十四条”，那么在识别[法律条款]和其他实体间的关系时，必须明确指出该[法律条款]隶属于哪个[法律]。例如，在上述示例中，识别关系时不能只单独提到“第二百七十四条”，而应该明确指出“《中华人民共和国刑事诉讼法》第二百七十四条”。***

-示例2-
文本：
婚后自行购买房产并希望独自拥有所有权。关于贷款部分的处理方式，是否由我个人承担？对方在这种情况下应采取何种行动以确保继承权？根据中国法律，在婚后自行购买房产并希望个人独自拥有所有权的情况下，如贷款由你个人承担，则该房产属于你的个人财产。你有权决定如何处理该房产，包括出售、赠予或遗赠给他人。然而，如果配偶在购买期间为该房产做出了贡献，比如支付了一部分首付款或参与了装修，你们可以签订协议明确双方的权益和义务。在你去世后，该房产将成为你的遗产，根据中国的继承法，你的配偶是你的合法继承人之一。但你可以在遗嘱中指定其他继承人，并决定继承比例。如果你们共同参与了贷款，那么根据协议或法律规定，在离婚或财产分割时对房产进行相应的分配。为确保继承权，你的配偶可以通过合法途径，如要求签订协议，公证或建立遗嘱等方式来保障相应的权益。
输出：
("entity"{tuple_delimiter}婚后个人购买的房产{tuple_delimiter}法律概念{tuple_delimiter}指在婚姻关系存续期间，由一方单独出资并以个人名义贷款购买的房产。根据中国法律，这种情况下的房产通常被视为购买方的个人财产，所有权人有权独立决定如何处置（如出售、赠予或遗赠）。该房产在所有权人去世后将成为其个人遗产的一部分。){record_delimiter} 
("entity"{tuple_delimiter}贷款{tuple_delimiter}金融产品{tuple_delimiter}为购买房产而获得的资金借贷。贷款的承担方式是决定房产所有权归属的关键因素。如果由一方个人完全承担，则房产倾向于被认定为个人财产；如果为共同贷款，则房产可能被视为夫妻共同财产，在分割时需进行相应分配。){record_delimiter} 
("entity"{tuple_delimiter}配偶{tuple_delimiter}法律主体{tuple_delimiter}婚姻关系中的另一方。即便房产为对方婚后个人购买，配偶依然拥有法定权利。根据《继承法》，配偶是法定第一顺序继承人，有权继承对方的遗产。如果配偶对该房产的购买或维护做出了贡献（如支付部分首付或参与装修），可以通过签订协议来明确自己的权益。){record_delimiter} 
("entity"{tuple_delimiter}继承权{tuple_delimiter}法律权利{tuple_delimiter}指根据法律或遗嘱继承死者遗产的权利。对于一方婚后个人购买的房产，其配偶拥有法定的继承权。然而，房产所有者可以通过订立遗嘱来指定其他继承人或调整继承份额，从而改变法定的继承结果。){record_delimiter} 
("entity"{tuple_delimiter}中国法律{tuple_delimiter}法律体系{tuple_delimiter}为婚后财产归属和继承问题提供法律依据的框架。它明确了在特定条件下（如个人出资和个人贷款）婚后购买的房产可被认定为个人财产，并通过《继承法》规定了配偶的法定继承人地位以及遗嘱的法律效力。){record_delimiter} 
("entity"{tuple_delimiter}遗嘱{tuple_delimiter}法律文件{tuple_delimiter}房产所有者生前订立的，用于指定其去世后财产（包括个人房产）如何分配的法律文书。通过遗嘱，所有者可以指定配偶以外的人为继承人，或调整法定继承人（包括配偶）的继承比例，其效力优先于法定继承。){record_delimiter} 
("entity"{tuple_delimiter}协议{tuple_delimiter}法律文件{tuple_delimiter}指夫妻双方为明确婚后财产权益和义务而签订的书面约定。当一方对另一方的个人房产有贡献时，可通过签订协议来保障自己的权益。同时，协议也是配偶用来确保自身继承权的一种有效法律途径。){record_delimiter} 
("relationship"{tuple_delimiter}婚后个人购买的房产{tuple_delimiter}中国法律{tuple_delimiter}中国法律界定了婚后个人购买房产的性质，规定在贷款由个人承担的情况下，该房产属于个人财产。){record_delimiter} 
("relationship"{tuple_delimiter}婚后个人购买的房产{tuple_delimiter}贷款{tuple_delimiter}贷款的承担方式直接影响婚后个人购买房产的财产归属，个人承担贷款是该房产被认定为个人财产的关键前提。){record_delimiter} 
("relationship"{tuple_delimiter}配偶{tuple_delimiter}继承权{tuple_delimiter}根据中国法律，配偶作为法定继承人，对另一方的个人财产（包括房产）拥有法定的继承权。){record_delimiter} 
("relationship"{tuple_delimiter}遗嘱{tuple_delimiter}继承权{tuple_delimiter}遗嘱可以改变法定的继承权分配规则，房产所有者可通过订立遗嘱来指定继承人或修改继承份额，从而影响配偶的实际继承权。){record_delimiter} 
("relationship"{tuple_delimiter}配偶{tuple_delimiter}婚后个人购买的房产{tuple_delimiter}配偶对另一方婚后个人购买的房产拥有法定继承权，并且如果对该房产有过贡献，可以通过协议来主张相应权益。){record_delimiter} 
("relationship"{tuple_delimiter}协议{tuple_delimiter}配偶{tuple_delimiter}协议是配偶用来保障自身在对方个人房产中权益的法律工具，可以通过协议明确因贡献产生的权益或确保继承权。){record_delimiter} 
("content_keywords"{tuple_delimiter}婚后财产, 个人财产, 房产所有权, 继承权, 配偶权益, 中国法律规定){completion_delimiter}
################

-真实数据-
文本：
{input_text}
输出：
"""

CONTINUE_EN: str = """MANY entities and relationships were missed in the last extraction.  \
Add them below using the same format:
"""

CONTINUE_ZH: str = """很多实体和关系在上一次的提取中可能被遗漏了。请在下面使用相同的格式添加它们："""

IF_LOOP_EN: str = """It appears some entities and relationships may have still been missed.  \
Answer YES | NO if there are still entities and relationships that need to be added.
"""

IF_LOOP_ZH: str = """看起来可能仍然遗漏了一些实体和关系。如果仍有实体和关系需要添加，请回答YES | NO。"""

KG_EXTRACTION_PROMPT: dict = {
    "English": {
        "TEMPLATE": TEMPLATE_EN,
        "CONTINUE": CONTINUE_EN,
        "IF_LOOP": IF_LOOP_EN,
    },
    "Chinese": {
        "TEMPLATE": TEMPLATE_ZH,
        "CONTINUE": CONTINUE_ZH,
        "IF_LOOP": IF_LOOP_ZH,
    },
    "FORMAT": {
        "tuple_delimiter": "<|>",
        "record_delimiter": "##",
        "completion_delimiter": "<|COMPLETE|>",
        "entity_types": "concept, date, location, keyword, organization, person, event, work, nature, artificial, \
science, technology, mission, gene",
        "language": "English",
    },
}


# TEMPLATE_ZH_AGRI: str = """你是一个NLP专家，擅长分析文本提取命名实体和关系。

# -目标-
# 给定一个实体类型列表和可能与列表相关的文本，从文本中识别所有这些类型的实体，以及这些实体之间所有的关系。
# 使用{language}作为输出语言。

# -步骤-
# 1. 识别所有实体。对于每个识别的实体，提取以下信息：
#    - entity_name：实体的名称，首字母大写
#    - entity_type：以下类型之一：[{entity_types}]
#    - entity_summary：实体的属性与活动的全面总结
#    将每个实体格式化为("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_summary>)
   
# 2. 从步骤1中识别的实体中，识别所有（源实体，目标实体）对，这些实体彼此之间*明显相关*。
#    对于每对相关的实体，提取以下信息：
#    - source_entity：步骤1中识别的源实体名称
#    - target_entity：步骤1中识别的目标实体名称
#    - relationship_summary：解释为什么你认为源实体和目标实体彼此相关
#    将每个关系格式化为("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_summary>)

# 3. 识别总结整个文本的主要概念、主题或话题的高级关键词。这些应该捕捉文档中存在的总体思想。
#    将内容级关键词格式化为("content_keywords"{tuple_delimiter}<high_level_keywords>)

# 4. 以中文返回步骤1和2中识别出的所有实体和关系的输出列表。使用**{record_delimiter}**作为列表分隔符。

# 5. 完成后，输出{completion_delimiter}

# ################
# -示例-
# ################
# -示例 1-
# 文本：
# ################
# 鲁镇的酒店的格局，是和别处不同的：都是当街一个曲尺形的大柜台，柜里面预备着热水，可以随时温酒。做工的人，傍午傍晚散了工，每每花四文铜钱，买一碗酒，——这是二十多年前的事，现在每碗要涨到十文，——靠柜外站着，热热的喝了休息；倘肯多花一文，便可以买一碟盐煮笋，或者茴香豆，做下酒物了，如果出到十几文，那就能买一样荤菜，但这些顾客，多是短衣帮，大抵没有这样阔绰。只有穿长衫的，才踱进店面隔壁的房子里，要酒要菜，慢慢地坐喝。
# ################
# 输出：
# ("entity"{tuple_delimiter}"鲁镇的酒店"{tuple_delimiter}"location"{tuple_delimiter}"鲁镇的酒店是一个特定地点，其格局独特，柜台形状为曲尺形，提供热水温酒服务。"){record_delimiter}
# ("entity"{tuple_delimiter}"曲尺形的大柜台"{tuple_delimiter}"keyword"{tuple_delimiter}"曲尺形的大柜台是鲁镇酒店内独特的设施，用于提供服务。"){record_delimiter}
# ("entity"{tuple_delimiter}"热水温酒"{tuple_delimiter}"keyword"{tuple_delimiter}"热水温酒是鲁镇酒店提供的一项服务，顾客可以随时温酒。"){record_delimiter}
# ("entity"{tuple_delimiter}"做工的人"{tuple_delimiter}"person"{tuple_delimiter}"做工的人是鲁镇酒店的常客，通常在工作结束后花四文铜钱买一碗酒，有时还会买一些下酒菜。"){record_delimiter}
# ("entity"{tuple_delimiter}"二十多年前的事"{tuple_delimiter}"date"{tuple_delimiter}"二十多年前的事是指过去的时间点，当时一碗酒的价格为四文铜钱。"){record_delimiter}
# ("entity"{tuple_delimiter}"现在"{tuple_delimiter}"date"{tuple_delimiter}"现在是指当前的时间点，与过去相比，一碗酒的价格涨到了十文。"){record_delimiter}
# ("entity"{tuple_delimiter}"短衣帮"{tuple_delimiter}"concept"{tuple_delimiter}"短衣帮是指做工的人，他们通常穿着短衣，经济条件有限。"){record_delimiter}
# ("entity"{tuple_delimiter}"穿长衫的"{tuple_delimiter}"person"{tuple_delimiter}"穿长衫的是鲁镇酒店的另一类顾客，他们经济条件较好，通常会进入店面隔壁的房间慢慢喝酒吃菜。"){record_delimiter}
# ("entity"{tuple_delimiter}"盐煮笋"{tuple_delimiter}"food"{tuple_delimiter}"盐煮笋是鲁镇酒店提供的一种下酒菜，顾客可以花一文铜钱购买。"){record_delimiter}
# ("entity"{tuple_delimiter}"茴香豆"{tuple_delimiter}"food"{tuple_delimiter}"茴香豆是鲁镇酒店提供的另一种下酒菜，顾客可以花一文铜钱购买。"){record_delimiter}
# ("entity"{tuple_delimiter}"荤菜"{tuple_delimiter}"food"{tuple_delimiter}"荤菜是鲁镇酒店提供的较为昂贵的菜品，顾客需要花十几文铜钱购买。"){record_delimiter}
# ("relationship"{tuple_delimiter}"鲁镇的酒店"{tuple_delimiter}"曲尺形的大柜台"{tuple_delimiter}"鲁镇的酒店内设有一个曲尺形的大柜台，用于提供服务。"){record_delimiter}
# ("relationship"{tuple_delimiter}"鲁镇的酒店"{tuple_delimiter}"热水温酒"{tuple_delimiter}"鲁镇的酒店提供热水温酒服务，顾客可以随时温酒。"){record_delimiter}
# ("relationship"{tuple_delimiter}"做工的人"{tuple_delimiter}"二十多年前的事"{tuple_delimiter}"做工的人在二十多年前花四文铜钱买一碗酒，反映了当时的生活成本。"){record_delimiter}
# ("relationship"{tuple_delimiter}"做工的人"{tuple_delimiter}"现在"{tuple_delimiter}"现在做工的人需要花十文铜钱买一碗酒，反映了物价的上涨。"){record_delimiter}
# ("relationship"{tuple_delimiter}"做工的人"{tuple_delimiter}"短衣帮"{tuple_delimiter}"做工的人属于短衣帮，通常经济条件有限。"){record_delimiter}
# ("relationship"{tuple_delimiter}"做工的人"{tuple_delimiter}"穿长衫的"{tuple_delimiter}"做工的人与穿长衫的形成对比，反映了社会阶层的差异。"){record_delimiter}
# ("relationship"{tuple_delimiter}"穿长衫的"{tuple_delimiter}"鲁镇的酒店"{tuple_delimiter}"穿长衫的顾客通常会进入鲁镇酒店的房间慢慢喝酒吃菜，享受更高级的服务。"){record_delimiter}
# ("content_keywords"{tuple_delimiter}"社会分层, 经济差距, 服务, 生活成本, 历史背景"){completion_delimiter}

# -示例 2-
# 文本：
# ################
# 黄华占是感温型常规稻品种，2016—2017 年在铅山县汪二镇作中稻示范种植综合表现优良。结合示范情况，对黄华占的特征特性作简单总结，在此基础上提出高产栽培技术，以期为该品种的推广种植提供参考。近年来，铅山县粮食生产紧紧围绕“稳产、优质、增效”的总体要求、大力实施优质稻推广，积极引导粮食生产由增产转向提质。我国杂交水稻技术世界领先、优质稻品种众多，在市场走势方面（尤其稻米行情清淡期），人们习惯性地北涨看长粒香、南涨看黄华占。黄华占是广东省农业科学院水稻研究所以黄新占/丰华占为亲本选育而成，分别通过粤、湘、鄂、浙、桂、琼等省审定。为了更好、更快地推广黄华占水稻，铅山县分别于2016 年、2017 年在汪二镇火田村试验示范种植黄华占近 5.87 hm^2 ，综合表现优良。现将黄华占水稻的特征特性及高产栽培技术介绍如下。
# ################
# 输出：
# ("entity"{tuple_delimiter}"黄华占"{tuple_delimiter}"work"{tuple_delimiter}"黄华占是一种感温型常规稻品种，由广东省农业科学院水稻研究所选育，通过多个省份审定，2016-2017年在铅山县汪二镇进行示范种植，表现优良。"){record_delimiter}
# ("entity"{tuple_delimiter}"2016—2017年"{tuple_delimiter}"date"{tuple_delimiter}"2016—2017年是黄华占在铅山县汪二镇进行示范种植的时间段。"){record_delimiter}
# ("entity"{tuple_delimiter}"铅山县"{tuple_delimiter}"location"{tuple_delimiter}"铅山县位于中国江西省，是黄华占水稻示范种植的地点之一。"){record_delimiter}
# ("entity"{tuple_delimiter}"汪二镇"{tuple_delimiter}"location"{tuple_delimiter}"汪二镇是铅山县的一个镇，2016-2017年在此进行了黄华占水稻的示范种植。"){record_delimiter}
# ("entity"{tuple_delimiter}"火田村"{tuple_delimiter}"location"{tuple_delimiter}"火田村是汪二镇的一个村庄，2016-2017年在此进行了黄华占水稻的试验示范种植。"){record_delimiter}
# ("entity"{tuple_delimiter}"广东省农业科学院水稻研究所"{tuple_delimiter}"organization"{tuple_delimiter}"广东省农业科学院水稻研究所是中国的一个科研机构，负责黄华占水稻的选育工作。"){record_delimiter}
# ("entity"{tuple_delimiter}"黄新占/丰华占"{tuple_delimiter}"work"{tuple_delimiter}"黄新占和丰华占是黄华占水稻的亲本，用于选育黄华占。"){record_delimiter}
# ("entity"{tuple_delimiter}"粤、湘、鄂、浙、桂、琼等省"{tuple_delimiter}"location"{tuple_delimiter}"这些省份通过了黄华占水稻的审定，表明该品种在这些地区具有良好的适应性和推广潜力。"){record_delimiter}
# ("entity"{tuple_delimiter}"高产栽培技术"{tuple_delimiter}"technology"{tuple_delimiter}"高产栽培技术是指为了提高黄华占水稻产量而采用的一系列农业技术措施。"){record_delimiter}
# ("entity"{tuple_delimiter}"稳产、优质、增效"{tuple_delimiter}"concept"{tuple_delimiter}"这是铅山县粮食生产的主要目标，强调了粮食生产的稳定、质量和效益。"){record_delimiter}
# ("entity"{tuple_delimiter}"优质稻推广"{tuple_delimiter}"mission"{tuple_delimiter}"优质稻推广是铅山县粮食生产的一个重要任务，旨在提高稻米的质量和市场竞争力。"){record_delimiter}
# ("entity"{tuple_delimiter}"杂交水稻技术"{tuple_delimiter}"technology"{tuple_delimiter}"杂交水稻技术是中国领先的世界级农业技术，用于提高水稻的产量和质量。"){record_delimiter}
# ("entity"{tuple_delimiter}"北涨看长粒香、南涨看黄华占"{tuple_delimiter}"concept"{tuple_delimiter}"这是市场对不同地区优质稻品种的习惯性关注点，北方面对长粒香，南方面对黄华占。"){record_delimiter}
# ("relationship"{tuple_delimiter}"黄华占"{tuple_delimiter}"2016—2017年"{tuple_delimiter}"黄华占在2016—2017年期间在铅山县进行了示范种植，展示了其优良的特性。"){record_delimiter}
# ("relationship"{tuple_delimiter}"黄华占"{tuple_delimiter}"铅山县"{tuple_delimiter}"黄华占在铅山县进行了示范种植，表现出了优良的适应性和产量。"){record_delimiter}
# ("relationship"{tuple_delimiter}"黄华占"{tuple_delimiter}"汪二镇"{tuple_delimiter}"黄华占在汪二镇进行了示范种植，这是其在铅山县示范种植的一部分。"){record_delimiter}
# ("relationship"{tuple_delimiter}"黄华占"{tuple_delimiter}"火田村"{tuple_delimiter}"黄华占在火田村进行了试验示范种植，这是其在汪二镇示范种植的一部分。"){record_delimiter}
# ("relationship"{tuple_delimiter}"黄华占"{tuple_delimiter}"广东省农业科学院水稻研究所"{tuple_delimiter}"黄华占是由广东省农业科学院水稻研究所选育的，该研究所负责其研发工作。"){record_delimiter}
# ("relationship"{tuple_delimiter}"黄华占"{tuple_delimiter}"黄新占/丰华占"{tuple_delimiter}"黄华占的亲本是黄新占和丰华占，这些亲本用于选育黄华占。"){record_delimiter}
# ("relationship"{tuple_delimiter}"黄华占"{tuple_delimiter}"粤、湘、鄂、浙、桂、琼等省"{tuple_delimiter}"黄华占通过了这些省份的审定，表明其在这些地区的适应性和推广潜力。"){record_delimiter}
# ("relationship"{tuple_delimiter}"黄华占"{tuple_delimiter}"高产栽培技术"{tuple_delimiter}"高产栽培技术是为了提高黄华占水稻产量而开发的技术措施。"){record_delimiter}
# ("relationship"{tuple_delimiter}"铅山县"{tuple_delimiter}"稳产、优质、增效"{tuple_delimiter}"铅山县的粮食生产目标是稳产、优质、增效，这些目标指导了黄华占的示范种植。"){record_delimiter}
# ("relationship"{tuple_delimiter}"铅山县"{tuple_delimiter}"优质稻推广"{tuple_delimiter}"铅山县实施了优质稻推广计划，黄华占是该计划的一部分。"){record_delimiter}
# ("relationship"{tuple_delimiter}"杂交水稻技术"{tuple_delimiter}"北涨看长粒香、南涨看黄华占"{tuple_delimiter}"杂交水稻技术的发展使得黄华占等优质稻品种在市场中受到关注。"){record_delimiter}
# ("content_keywords"{tuple_delimiter}"黄华占, 水稻种植, 高产栽培技术, 优质稻推广, 地区适应性, 市场趋势, 技术影响"){completion_delimiter}

# -真实数据-
# 实体类型：{entity_types}
# 文本：{input_text}
# ################
# 输出：
# """

# CONTINUE_EN: str = """MANY entities and relationships were missed in the last extraction.  \
# Add them below using the same format:
# """
