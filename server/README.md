---
library_name: peft
license: other
base_model: /mnt/disk2/aolin.guo/graduate_agent/server/model-dir
tags:
- base_model:adapter:/mnt/disk2/aolin.guo/graduate_agent/server/model-dir
- llama-factory
- lora
- transformers
pipeline_tag: text-generation
model-index:
- name: server
  results: []
---

<!-- This model card has been generated automatically according to the information the Trainer had access to. You
should probably proofread and complete it, then remove this comment. -->

# server

This model is a fine-tuned version of [/mnt/disk2/aolin.guo/graduate_agent/server/model-dir](https://huggingface.co//mnt/disk2/aolin.guo/graduate_agent/server/model-dir) on the AAA_training dataset.

## Model description

More information needed

## Intended uses & limitations

More information needed

## Training and evaluation data

More information needed

## Training procedure

### Training hyperparameters

The following hyperparameters were used during training:
- learning_rate: 0.0001
- train_batch_size: 1
- eval_batch_size: 8
- seed: 42
- distributed_type: multi-GPU
- num_devices: 2
- gradient_accumulation_steps: 4
- total_train_batch_size: 8
- total_eval_batch_size: 16
- optimizer: Use OptimizerNames.ADAMW_TORCH_FUSED with betas=(0.9,0.999) and epsilon=1e-08 and optimizer_args=No additional optimizer arguments
- lr_scheduler_type: cosine
- lr_scheduler_warmup_ratio: 0.1
- num_epochs: 3.0

### Training results



### Framework versions

- PEFT 0.17.1
- Transformers 4.57.1
- Pytorch 2.9.0+cu128
- Datasets 4.0.0
- Tokenizers 0.22.1