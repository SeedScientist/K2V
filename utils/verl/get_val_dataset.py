"""
Since verl forcibly requires specifying a validation set", 
we randomly sample data from training set as the validation set.
"""

import random
import datasets

def sample_dataset(train_file_path, val_file_path, sample_size, seed=42):
    """
    Sample n rows randomly from a parquet file and save as a new parquet file.
    Args:
        train_file_path: Path to the input parquet file
        val_file_path: Path where the sampled dataset will be saved
        sample_size: Number of samples to extract
        seed: Random seed for reproducibility
    """

    random.seed(seed)
    dataset = datasets.Dataset.from_parquet(train_file_path)
    
    total_rows = len(dataset)
    if sample_size > total_rows:
        print(f"Warning: Sample size {sample_size} exceeds dataset size {total_rows}. Using all data.")
        sample_size = total_rows
    
    # Get random indices
    indices = random.sample(range(total_rows), sample_size)
    indices_set = set(indices)
    
    # Extract the samples for validation
    sampled_dataset = dataset.select(indices)
    
    # Update the split field to "test" for all samples in the validation dataset
    def update_split(example):
        example['extra_info']['split'] = 'test'
        return example
    
    sampled_dataset = sampled_dataset.map(update_split)
    
    # Save validation dataset
    sampled_dataset.to_parquet(val_file_path)
    
    # Remove sampled indices from training dataset
    remaining_indices = [i for i in range(total_rows) if i not in indices_set]
    remaining_dataset = dataset.select(remaining_indices)
    
    # Overwrite the original training file with remaining data
    remaining_dataset.to_parquet(train_file_path)
    
    print(f"Successfully created validation dataset with {sample_size} samples at {val_file_path}")
    print(f"Updated training dataset with {len(remaining_dataset)} samples")

    return 

if __name__ == "__main__":
    train_file_path = ''
    val_file_path = ''
    sample_size = 32
    seed = 42
    
    sample_dataset(train_file_path, val_file_path, sample_size, seed)
