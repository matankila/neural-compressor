import os
import shutil
import unittest

import torch
import torchvision
import torch.nn as nn

from lpot.data import DATASETS
from lpot.experimental.data.dataloaders.pytorch_dataloader import PyTorchDataLoader

def build_fake_yaml():
    fake_yaml = """
    model:
      name: imagenet_prune
      framework: pytorch

    pruning:
      approach:
        weight_compression:
          initial_sparsity: 0.0
          target_sparsity: 0.97
          start_epoch: 0
          end_epoch: 4
          pruners:
            - !Pruner
                start_epoch: 1
                end_epoch: 3
                prune_type: basic_magnitude
                names: ['layer1.0.conv1.weight']

            - !Pruner
                target_sparsity: 0.6
                prune_type: basic_magnitude
                update_frequency: 2
                names: ['layer1.0.conv2.weight']
    evaluation:
      accuracy:
        metric:
          topk: 1
    """
    with open('fake.yaml', 'w', encoding="utf-8") as f:
        f.write(fake_yaml)


class TestPruning(unittest.TestCase):

    model = torchvision.models.resnet18()

    @classmethod
    def setUpClass(cls):
        build_fake_yaml()

    @classmethod
    def tearDownClass(cls):
        os.remove('fake.yaml')
        shutil.rmtree('./saved', ignore_errors=True)
        shutil.rmtree('runs', ignore_errors=True)

    def test_pruning(self):
        from lpot.experimental import Pruning, common
        prune = Pruning('fake.yaml')
        datasets = DATASETS('pytorch')
        dummy_dataset = datasets['dummy'](shape=(100, 3, 224, 224), low=0., high=1., label=True)
        dummy_dataloader = PyTorchDataLoader(dummy_dataset)

        def training_func_for_lpot(model):
            model_ = model.model
            epochs = 16
            iters = 30
            criterion = nn.CrossEntropyLoss()
            optimizer = torch.optim.SGD(model_.parameters(), lr=0.0001)
            for nepoch in range(epochs):
                model_.train()
                cnt = 0
                prune.on_epoch_begin(nepoch)
                for image, target in dummy_dataloader:
                    prune.on_batch_begin(cnt)
                    print('.', end='')
                    cnt += 1
                    output = model_(image)
                    loss = criterion(output, target)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    prune.on_batch_end()
                    if cnt >= iters:
                        break
                prune.on_epoch_end()
        prune.model = common.Model(self.model)
        prune.pruning_func = training_func_for_lpot
        prune.eval_dataloader = dummy_dataloader
        prune.train_dataloader = dummy_dataloader
        _ = prune()

    def test_pruning_external(self):
        from lpot.experimental import common
        from lpot import Pruning
        prune = Pruning('fake.yaml')
        datasets = DATASETS('pytorch')
        dummy_dataset = datasets['dummy'](shape=(100, 3, 224, 224), low=0., high=1., label=True)
        dummy_dataloader = PyTorchDataLoader(dummy_dataset)

        def training_func_for_lpot(model):
            model_ = model.model
            epochs = 16
            iters = 30
            criterion = nn.CrossEntropyLoss()
            optimizer = torch.optim.SGD(model_.parameters(), lr=0.0001)
            for nepoch in range(epochs):
                model_.train()
                cnt = 0
                prune.on_epoch_begin(nepoch)
                for image, target in dummy_dataloader:
                    prune.on_batch_begin(cnt)
                    print('.', end='')
                    cnt += 1
                    output = model_(image)
                    loss = criterion(output, target)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    prune.on_batch_end()
                    if cnt >= iters:
                        break
                prune.on_epoch_end()
        prune.model = common.Model(self.model)
        prune.pruning_func = training_func_for_lpot
        prune.eval_dataloader = dummy_dataloader
        prune.train_dataloader = dummy_dataloader
        _ = prune(common.Model(self.model), \
                  train_dataloader=dummy_dataloader, \
                  pruning_func=training_func_for_lpot, \
                  eval_dataloader=dummy_dataloader)

if __name__ == "__main__":
    unittest.main()
