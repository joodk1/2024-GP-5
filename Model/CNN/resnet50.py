# -*- coding: utf-8 -*-
"""ResNet50.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1XYaAV5-RYEzMzEP9hGZUQVhOAEU3k_uq
"""

import os
import cv2
import numpy as np
from tensorflow.keras.utils import Sequence
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GlobalAveragePooling2D, LSTM, Dense, TimeDistributed
from tensorflow.keras.applications import ResNet50
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix

class FrameDataGenerator(Sequence):
    def __init__(self, base_path, labels, num_frames, height, width, batch_size=32, shuffle=True):
        self.base_path = base_path
        self.labels = labels
        self.num_frames = num_frames
        self.height = height
        self.width = width
        self.batch_size = batch_size
        self.shuffle = shuffle

        # Recursively list directories containing the videos
        self.video_folders = []
        for label_dir in os.listdir(base_path):
            label_dir_path = os.path.join(base_path, label_dir)
            if os.path.isdir(label_dir_path):
                for video_dir in os.listdir(label_dir_path):
                    video_dir_path = os.path.join(label_dir_path, video_dir)
                    if os.path.isdir(video_dir_path):
                        self.video_folders.append((video_dir_path, self.labels[label_dir]))

        if self.shuffle:
            np.random.shuffle(self.video_folders)

    def __len__(self):
        return int(np.ceil(len(self.video_folders) / self.batch_size))

    def __getitem__(self, index):
        batch_paths_labels = self.video_folders[index * self.batch_size:(index + 1) * self.batch_size]
        X = np.empty((len(batch_paths_labels), self.num_frames, self.height, self.width, 3), dtype=np.float32)
        y = np.empty(len(batch_paths_labels), dtype=int)

        for i, (folder_path, label) in enumerate(batch_paths_labels):
            frame_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.jpg')])[:self.num_frames]
            frames = [cv2.resize(cv2.imread(os.path.join(folder_path, f)), (self.width, self.height)) for f in frame_files]
            frames = [frame for frame in frames if frame is not None]
            if len(frames) < self.num_frames:
                frames += [np.zeros((self.height, self.width, 3), dtype=np.float32)] * (self.num_frames - len(frames))
            X[i] = np.stack(frames, axis=0)
            y[i] = label

        return X, y

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.video_folders)


def build_model(input_shape):
    base_model = ResNet50(weights='imagenet', include_top=False, input_shape=input_shape[1:], pooling='avg')
    base_model.trainable = False
    model = Sequential([
        TimeDistributed(base_model, input_shape=input_shape),
        LSTM(64),
        Dense(128, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    return model

# Define constants and dataset paths
num_frames = 10
height = 299
width = 299
batch_size = 32
train_base_path = "/content/drive/MyDrive/Dataset_Full/Train"
validation_base_path = "/content/drive/MyDrive/Dataset_Full/Validation"
test_base_path = "/content/drive/MyDrive/Dataset_Full/Test"
labels = {'Authentic': 0, 'Manipulated': 1}

# Initialize data generators
train_gen = FrameDataGenerator(train_base_path, labels, num_frames, height, width, batch_size, shuffle=True)
validation_gen = FrameDataGenerator(validation_base_path, labels, num_frames, height, width, batch_size, shuffle=False)
test_gen = FrameDataGenerator(test_base_path, labels, num_frames, height, width, batch_size, shuffle=False)

# Build, compile, and train the model
model = build_model((num_frames, height, width, 3))
model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
history = model.fit(train_gen, epochs=20, validation_data=validation_gen)

# Evaluate the model on the test set
test_loss, test_accuracy = model.evaluate(test_gen)
print(f"Test Loss: {test_loss}, Test Accuracy: {test_accuracy}")

# Plot training and validation accuracy
plt.plot(history.history['accuracy'], label='Training Accuracy', color='darkgreen', linestyle='-', marker='o')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy', color='limegreen', linestyle='--', marker='x')
plt.title('Training and Validation Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()
plt.show()

# Plot training and validation loss
plt.plot(history.history['loss'], label='Training Loss', color='darkgreen', linestyle='-', marker='o')
plt.plot(history.history['val_loss'], label='Validation Loss', color='limegreen', linestyle='--', marker='x')
plt.title('Training and Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.show()

# Prediction and Evaluation
true_labels, predictions = [], []
for X, y in test_gen:
    preds = model.predict(X)
    preds_binary = (preds > 0.5).astype(int).flatten()
    true_labels.extend(y)
    predictions.extend(preds_binary)

# Classification report
print(classification_report(true_labels, predictions))

# Confusion matrix
conf_matrix = confusion_matrix(true_labels, predictions)
plt.figure(figsize=(8, 6))
sns.heatmap(conf_matrix, annot=True, fmt="d", cmap='Greens',
            xticklabels=['Authentic', 'Manipulated'],
            yticklabels=['Authentic', 'Manipulated'])
plt.xlabel('Predicted Label')
plt.ylabel('True Label')
plt.title('Confusion Matrix')
plt.show()

# Save the model
model.save("/content/drive/MyDrive/Models/ResNet50_Model_Web2.h5", save_format='h5')