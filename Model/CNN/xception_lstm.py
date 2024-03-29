# -*- coding: utf-8 -*-
"""xception_LSTM.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1nlp11r1uJAOypBrIdG4M7R0itOMoe3LA
"""

import os
import cv2
import random
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import Xception
from tensorflow.keras import layers, models
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder

# load data
def load_data(data_dir, target_size=(299, 299), max_frames_per_video=10):
    data = []
    labels = []
    label_to_index = {}
    index = 0
    for label in os.listdir(data_dir):
        label_dir = os.path.join(data_dir, label)
        label_to_index[label] = index
        for video_folder in os.listdir(label_dir):
            frames = []
            video_path = os.path.join(label_dir, video_folder)
            for frame_file in sorted(os.listdir(video_path))[:max_frames_per_video]:
                frame_path = os.path.join(video_path, frame_file)
                frame = cv2.imread(frame_path)
                frame = cv2.resize(frame, target_size)
                frames.append(frame)
            if len(frames) < max_frames_per_video:
                frames.extend([np.zeros_like(frames[0])] * (max_frames_per_video - len(frames)))
            data.append(frames)
            labels.append(index)
        index += 1
    return np.array(data), np.array(labels), label_to_index

# Load training and testing data
train_data, train_labels, label_to_index = load_data("/content/drive/MyDrive/Dataset_Faces/Train")
test_data, test_labels, _ = load_data("/content/drive/MyDrive/Dataset_Faces/Test")

# Reshape train_data and test_data
train_data = train_data.reshape((-1, 299, 299, 3))
test_data = test_data.reshape((-1, 299, 299, 3))

# Verify data shapes
print("Shape of train_data:", train_data.shape)
print("Shape of train_labels:", train_labels.shape)
print("Shape of test_data:", test_data.shape)
print("Shape of test_labels:", test_labels.shape)

# Encode string labels to integers
label_encoder = LabelEncoder()
train_labels_encoded = label_encoder.fit_transform(train_labels)
test_labels_encoded = label_encoder.transform(test_labels)

# Shuffle training data based on the length of label array
random.seed(42)
idx = list(range(len(train_labels_encoded)))
random.shuffle(idx)
train_data = train_data[idx]
train_labels_encoded = train_labels_encoded[idx]

# Load pre-trained Xception model
base_model = Xception(weights='imagenet', include_top=False, input_shape=(299, 299, 3))

# Freeze the layers of the pre-trained model
base_model.trainable = False

# Add custom classification head
x = base_model.output
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dense(64, activation='relu')(x)
x = layers.Dropout(0.5)(x)
output = layers.Dense(2, activation='softmax')(x)

# Create the model
model = models.Model(inputs=base_model.input, outputs=output)

# Compile the model
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# Train the model
history = model.fit(train_data, train_labels_encoded, epochs=10, batch_size=80, validation_split=0.2)

# Plot loss and accuracy over epochs
plt.figure(figsize=(12, 5))

# Plot training & validation loss
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

# Plot training & validation accuracy
plt.subplot(1, 2, 2)
plt.plot(history.history['accuracy'], label='Training Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('Model Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()

plt.show()

# Evaluate the model on test data
test_predictions_frames = model.predict(test_data)
test_predictions_frames = np.argmax(test_predictions_frames, axis=1)

# Majority voting aggregation
test_predictions_videos = []
for i in range(0, len(test_predictions_frames), 10):
    frame_predictions = test_predictions_frames[i:i+10]
    video_prediction = np.bincount(frame_predictions).argmax()
    test_predictions_videos.append(video_prediction)

# Convert list to numpy array
test_predictions_videos = np.array(test_predictions_videos)

# Check if the number of samples match
assert test_labels_encoded.shape[0] == test_predictions_videos.shape[0], "Number of samples in test_labels_encoded and test_predictions_videos do not match"

# Generate classification report
print("Classification Report:")
print(classification_report(test_labels_encoded, test_predictions_videos))

# Generate confusion matrix (heat map)
cm = confusion_matrix(test_labels_encoded, test_predictions_videos)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=label_to_index.keys(), yticklabels=label_to_index.keys())
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.title('Confusion Matrix')
plt.show()

# Save the model
model.save("/content/drive/MyDrive/Models/Xception_Feature_Extractor")