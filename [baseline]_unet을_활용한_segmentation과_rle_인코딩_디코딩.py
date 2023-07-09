# -*- coding: utf-8 -*-
"""[Baseline]_Unet을 활용한 Segmentation과 RLE 인코딩_디코딩.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1_yyHvav8CknGBcd6TaOYCrfoFeLFopoF

## Import
"""

import os
import cv2
import pandas as pd
import numpy as np

os.environ['KMP_DUPLICATE_LIB_OK']='True'

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

from tqdm import tqdm
import albumentations as A
from albumentations.pytorch import ToTensorV2

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

import custom_dataset
#import model_train
import utils

"""## Utils"""

# RLE 디코딩 함수


"""## Custom Dataset"""


"""## Data Loader"""

# df_train = pd.read_csv('./sample_data/mnist_train_small.csv', header=None)
# df_test = pd.read_csv('./sample_data/mnist_test.csv', header=None)

# train_labels = df_train.iloc[:, 0]
# train_images = df_train.iloc[:, 1:]
# test_labels = df_test.iloc[:, 0]
# test_images = df_test.iloc[:, 1:]

transform = A.Compose(
    [
        A.Resize(224, 224),
        A.Normalize(),
        ToTensorV2()
    ]
)

dataset = custom_dataset.SatelliteDataset(csv_file='./open/train.csv', transform=transform)
dataloader = DataLoader(dataset, batch_size=16, shuffle=True, num_workers=4)

#dataimage = DataLoader("./open/train_img/TRAIN.*", with_info=True)

"""## Define Model"""

# U-Net의 기본 구성 요소인 Double Convolution Block을 정의합니다.
def double_conv(in_channels, out_channels):
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, 3, padding=1),
        nn.ReLU(inplace=True),
        nn.Conv2d(out_channels, out_channels, 3, padding=1),
        nn.ReLU(inplace=True)
    )

# 간단한 U-Net 모델 정의
class UNet(nn.Module):
    def __init__(self):
        super(UNet, self).__init__()
        self.dconv_down1 = double_conv(3, 64)
        self.dconv_down2 = double_conv(64, 128)
        self.dconv_down3 = double_conv(128, 256)
        self.dconv_down4 = double_conv(256, 512)

        self.maxpool = nn.MaxPool2d(2)
        self.upsample = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)

        self.dconv_up3 = double_conv(256 + 512, 256)
        self.dconv_up2 = double_conv(128 + 256, 128)
        self.dconv_up1 = double_conv(128 + 64, 64)

        self.conv_last = nn.Conv2d(64, 1, 1)

    def forward(self, x):
        conv1 = self.dconv_down1(x)
        x = self.maxpool(conv1)

        conv2 = self.dconv_down2(x)
        x = self.maxpool(conv2)

        conv3 = self.dconv_down3(x)
        x = self.maxpool(conv3)

        x = self.dconv_down4(x)

        x = self.upsample(x)
        x = torch.cat([x, conv3], dim=1)

        x = self.dconv_up3(x)
        x = self.upsample(x)
        x = torch.cat([x, conv2], dim=1)

        x = self.dconv_up2(x)
        x = self.upsample(x)
        x = torch.cat([x, conv1], dim=1)

        x = self.dconv_up1(x)

        out = self.conv_last(x)

        return out

"""## Model Train"""

# def train():
#     # model 초기화
#     model = UNet().to(device)

#     # loss function과 optimizer 정의
#     criterion = torch.nn.BCEWithLogitsLoss()
#     optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

#     #drive.mount('/content/drive')
#     #images, labels = next(iter(dataloader))

#     # training loop
#     for epoch in range(1):  # 10 에폭 동안 학습합니다. ##########
#         model.train()
#         epoch_loss = 0
#         for images, masks in tqdm(dataloader): ######
#             images = images.float().to(device)
#             masks = masks.float().to(device)

#             optimizer.zero_grad()
#             outputs = model(images)
#             loss = criterion(outputs, masks.unsqueeze(1))
#             loss.backward()
#             optimizer.step()

#             epoch_loss += loss.item()

#         print(f'Epoch {epoch+1}, Loss: {epoch_loss/len(dataloader)}')

#     """## Inference"""

#     test_dataset = SatelliteDataset(csv_file='./open/test.csv', transform=transform, infer=True)
#     test_dataloader = DataLoader(test_dataset, batch_size=16, shuffle=False, num_workers=4)

#     with torch.no_grad():
#         model.eval()
#         result = []
#         for images in tqdm(test_dataloader):
#             images = images.float().to(device)

#             outputs = model(images)
#             masks = torch.sigmoid(outputs).cpu().numpy()
#             masks = np.squeeze(masks, axis=1)
#             masks = (masks > 0.35).astype(np.uint8) # Threshold = 0.35

#             for i in range(len(images)):
#                 mask_rle = rle_encode(masks[i])
#                 if mask_rle == '': # 예측된 건물 픽셀이 아예 없는 경우 -1
#                     result.append(-1)
#                 else:
#                     result.append(mask_rle)
#     submit = pd.read_csv('./open/sample_submission.csv')
#     submit['mask_rle'] = result

#     submit.to_csv('./submit.csv', index=False)

# model 초기화
model = UNet().to(device)

# # loss function과 optimizer 정의
criterion = torch.nn.BCEWithLogitsLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# #drive.mount('/content/drive')
# #images, labels = next(iter(dataloader))

# # training loop
for epoch in range(1):  # 10 에폭 동안 학습합니다.
    model.train()
    epoch_loss = 0
    for images, masks in tqdm(dataloader):
        images = images.float().to(device)
        masks = masks.float().to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, masks.unsqueeze(1))
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()

    print(f'Epoch {epoch+1}, Loss: {epoch_loss/len(dataloader)}')

"""## Inference"""

test_dataset = custom_dataset.SatelliteDataset(csv_file='./open/test.csv', transform=transform, infer=True)
test_dataloader = DataLoader(test_dataset, batch_size=16, shuffle=False, num_workers=4)

with torch.no_grad():
    model.eval()
    result = []
    for images in tqdm(test_dataloader):
        images = images.float().to(device)

        outputs = model(images)
        masks = torch.sigmoid(outputs).cpu().numpy()
        masks = np.squeeze(masks, axis=1)
        masks = (masks > 0.35).astype(np.uint8) # Threshold = 0.35

        for i in range(len(images)):
            mask_rle = utils.rle_encode(masks[i])
            if mask_rle == '': # 예측된 건물 픽셀이 아예 없는 경우 -1
                result.append(-1)
            else:
                result.append(mask_rle)

"""## Submission"""

submit = pd.read_csv('./open/sample_submission.csv')
submit['mask_rle'] = result

submit.to_csv('./submit.csv', index=False)

# if __name__ == "__main__":
#     # parameters={}
#     train()