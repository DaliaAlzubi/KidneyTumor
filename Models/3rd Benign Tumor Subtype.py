# -*- coding: utf-8 -*-
"""3_Model_Benign_Subtype.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1V1_qUiY8vLxWqIDTQGg8fIx95tBgE6T4
"""

# -*- coding: utf-8 -*-
import seaborn as sns; sns.set(color_codes=True)  # visualization tool
import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt 
import os

import statistics
import collections
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials
from datetime import datetime
from datetime import date
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import (
                    MultinomialNB, 
                    GaussianNB, 
                    BernoulliNB
                    )
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import confusion_matrix
from sklearn.svm import (
                    SVC, 
                    NuSVC, 
                    LinearSVC
                    )
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing  import StandardScaler
from sklearn.decomposition import PCA
from sklearn import tree
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report,confusion_matrix

from IPython.display import display 
from xgboost import XGBClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.svm import SVC

import keras
from keras.models import Sequential , Model
from keras.layers import (
                        Dense,
                        Conv2D,
                        MaxPool2D,
                        Flatten,
                        Dropout,
                        MaxPooling2D,
                        Input,
                        Conv2DTranspose,
                        Concatenate,
                        BatchNormalization,
                        UpSampling2D,
                        AveragePooling2D,
                        GlobalAveragePooling2D,
                        Activation,
                        ZeroPadding2D
                        )
from keras.preprocessing.image import ImageDataGenerator
from keras.optimizers import Adam , SGD
from keras.layers.merge import concatenate
from keras.layers.advanced_activations import LeakyReLU
from keras.callbacks import ModelCheckpoint, ReduceLROnPlateau, EarlyStopping
from keras import backend as K
from keras.utils.np_utils import to_categorical # convert to one-hot-encoding

#from keras.utils import plot_model

from sklearn.metrics import classification_report,confusion_matrix
from PIL import Image
import tensorflow as tf
import glob
import random
import cv2
from random import shuffle
import itertools
import imutils

!unzip sample_data/images_data.zip -d sample_data/

auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)

patient_info = drive.CreateFile({'id':"1dN1peOSeugjLLzzazh4yGoy_g1LBlzp7"})
patient_info.GetContentFile("patient_info.csv")
patient_info = pd.read_csv("patient_info.csv")

patient_info = patient_info[patient_info['Tumor_Type']== "Benign"]

patient_info.info()

cleanup_nums = {
    "Tumor_Class":{'RCC ':'RCC' , 'Angiomyolipoma ':'Angiomyolipoma' , "Null":"Uninfected" ,'Angiomyolipoma and Adenomas':'Angiomyolipoma' },
}
patient_info = patient_info.replace(cleanup_nums)
patient_info = patient_info[patient_info['Tumor_Class']!="Lipomas"]

Tumor_Type_flg = patient_info['Tumor_Class'].value_counts()
display(Tumor_Type_flg)
fig = plt.figure(figsize =(6, 9))
plt.pie( Tumor_Type_flg , labels=Tumor_Type_flg.index , autopct='%1.1f%%', shadow=True, startangle=90 )
plt.title('Tumor Class')
plt.show()

patient_info["Tumor_class_label"]= patient_info["Tumor_Class"]
cleanup_nums = {
    "Tumor_class_label":{"Adenoma":0 , 'Angiomyolipoma':1 }
}
patient_info = patient_info.replace(cleanup_nums)
del cleanup_nums

patient_info["Tumor_class_label"].value_counts()

labels = {0:"Adenoma",1:"Angiomyolipoma"}

def crop_contour(image, plot=False):
    
    # Convert the image to grayscale, and blur it slightly
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Threshold the image, then perform a series of erosions +
    # dilations to remove any small regions of noise
    thresh = cv2.threshold(gray, 45, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.erode(thresh, None, iterations=2)
    thresh = cv2.dilate(thresh, None, iterations=2)

    # Find contours in thresholded image, then grab the largest one
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    c = max(cnts, key=cv2.contourArea)
  
    # Find the extreme points
    extLeft = tuple(c[c[:, :, 0].argmin()][0])
    extRight = tuple(c[c[:, :, 0].argmax()][0])
    extTop = tuple(c[c[:, :, 1].argmin()][0])
    extBot = tuple(c[c[:, :, 1].argmax()][0])
    
    # crop new image out of the original image using the four extreme points (left, right, top, bottom)
    new_image = image[extTop[1]:extBot[1], extLeft[0]:extRight[0]]            

    if plot:
        plt.figure()

        plt.subplot(1, 2, 1)
        plt.imshow(image)
        
        plt.tick_params(axis='both', which='both', 
                        top=False, bottom=False, left=False, right=False,
                        labelbottom=False, labeltop=False, labelleft=False, labelright=False)
        
        plt.title('Original Image')
        plt.subplot(1, 2, 2)
        plt.imshow(new_image)

        plt.tick_params(axis='both', which='both', 
                        top=False, bottom=False, left=False, right=False,
                        labelbottom=False, labeltop=False, labelleft=False, labelright=False)
        plt.title('Cropped Image')
        plt.show()

    return new_image

def get_data (data_dir , target ):
    X = list()
    y=list()
    img_size = 256
    for index, row in patient_info.iterrows():
        path = os.path.join(data_dir, str (row['Patient_Num']))
        label = row[target]
        for img in os.listdir(path):
            try:
                img_arr = cv2.imread(os.path.join(path, img))[...,::-1] #convert BGR to RGB format
                #crop_contour_img = crop_contour(img_arr, False )
                resized_arr = cv2.resize(img_arr, (img_size, img_size)) # Reshaping images to preferred size   
                             
                X.append(resized_arr)
                y.append(label)
            except Exception as e:
                print(e , row['Patient_Num'] )
    return X , y

X , y  = get_data("sample_data/Dalia_Data/", target = "Tumor_class_label")

dict(zip(list(y),[list(y).count(i) for i in list(y)]))

plt.figure(figsize = (5,5))
plt.imshow(X[20])
plt.title(labels[y[10]])
plt.show()

plt.figure(figsize = (5,5))
plt.imshow(X[2100])
plt.title(labels[y[2100]])
plt.show()

x_train, x_test, y_train, y_test = train_test_split(X, y, test_size = 0.20)
x_train, x_val, y_train, y_val = train_test_split(x_train, y_train, test_size = 0.20)

print ("Number images for training : {}".format(len (x_train)))
print ("Number images for testing : {}".format(len (x_test)))
print ("Number images for Validation : {}".format(len (x_val)))

dict(zip(list(y_val),[list(y_val).count(i) for i in list(y_val)]))

def data_prepare (X , y , folder_name , labels ) :
    path = "sample_data/{}".format(folder_name)
    os.mkdir(path)
    # create folder for labels 
    for key , value in labels.items()  : 
        path = "sample_data/{}/{}".format(folder_name,value)
        os.mkdir(path)

    if len (X) != len (y) : 
      print ("error size data X and y is not equal")
      return 

    for index , value in enumerate(y) : 
      im = Image.fromarray(X[index])
      path = "sample_data/{}/{}/{}.jpeg".format(folder_name,labels[value],str(index))
      im.save(path)
    return

data_prepare (X=x_train ,y=y_train ,folder_name="train", labels=labels )
data_prepare (X=x_test ,y=y_test ,folder_name="test", labels=labels )
data_prepare (X=x_val ,y=y_val ,folder_name="validation", labels=labels )

## Genration Images 

train_datagen = ImageDataGenerator(rescale = 1./255,
                                   shear_range = 0.2,
                                   zoom_range = 0.2,
                                   horizontal_flip = True)


test_datagen = ImageDataGenerator(rescale = 1./255)

training_set = train_datagen.flow_from_directory('/content/sample_data/train',
                                                 target_size = (224, 224),
                                                 batch_size = 32,
                                                 class_mode = 'binary')

test_set = test_datagen.flow_from_directory('/content/sample_data/test',
                                            target_size = (224,224),
                                            batch_size = 32,
                                            class_mode = 'binary')

model= Sequential()
model.add(Conv2D(32, (3, 3), input_shape = (224, 224, 3), activation = 'relu'))
model.add(MaxPooling2D(pool_size = (2, 2)))
model.add(Flatten())
model.add(Dense(units = 128, activation = 'relu'))
model.add(Dense(units = 2, activation = 'softmax'))
model.compile(optimizer='adam', loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True), metrics=['accuracy'])

model.summary()

hist=model.fit(training_set,
                         steps_per_epoch = (2072 /128),
                         epochs = 50,
                         validation_data = test_set,
                         validation_steps = (414 /128))

model.save("Tumer_Benign.h5")
np.save('Tumer_Benign_history_traning.npy',hist.history)

loss,accuracy=model.evaluate(test_set)
print (f"Test Loss     = {loss}")
print (f"Test Accuracy = {accuracy}")

print('Training Set Clases')
print(training_set.class_indices)
print("=="*10)
print('Testing Set Clases')
print(test_set.class_indices)

from keras.preprocessing import image

path='/content/sample_data/validation/Adenoma'
l_Adenoma =[]

filelist= [file for file in os.listdir(path) if file.endswith('.jpeg')]
y_Adenoma =[0]*len(filelist)
print ("Number of images for Adenoma :" , len (filelist))

for img in filelist:
  test_image = image.load_img(os.path.join(path, img),target_size = (224, 224))
  test_image = image.img_to_array(test_image)
  test_image = np.expand_dims(test_image, axis = 0)
  l_Adenoma.append(test_image)

l_Adenoma_result=[]
for i in range(len(l_Adenoma)):
  xx = model.predict_classes(l_Adenoma[i])
  l_Adenoma_result.append(xx)

l_Adenoma_draw=[]
for i in range(len(l_Adenoma_result)):
    if(l_Adenoma_result[i][0] == 0):
        l_Adenoma_draw.append("Adenoma")
    else :
        l_Adenoma_draw.append("Angiomyolipoma")

display('==='*10)
display(dict(zip(list(l_Adenoma_draw),[list(l_Adenoma_draw).count(i) for i in list(l_Adenoma_draw)])))
display('==='*10)

sns.set_style('darkgrid')
sns.countplot(l_Adenoma_draw)
plt.show()

path='/content/sample_data/validation/Angiomyolipoma'
l_Angiomyolipoma =[]

filelist= [file for file in os.listdir(path) if file.endswith('.jpeg')]
y_Angiomyolipoma =[1]*len(filelist)
print ("Number of images for Angiomyolipoma :" , len (filelist))

for img in filelist:
  test_image = image.load_img(os.path.join(path, img), target_size = (224, 224))
  test_image = image.img_to_array(test_image)
  test_image = np.expand_dims(test_image, axis = 0)
  l_Angiomyolipoma.append(test_image)

l_Angiomyolipoma_result=[]
for i in range(len(l_Angiomyolipoma)):
  xx = model.predict_classes(l_Angiomyolipoma[i])
  l_Angiomyolipoma_result.append(xx)

l_Angiomyolipoma_draw=[]
for i in range(len(l_Angiomyolipoma_result)):

    if (l_Angiomyolipoma_result[i][0] == 1):
        l_Angiomyolipoma_draw.append("Angiomyolipoma")
    else:
        l_Angiomyolipoma_draw.append("Adenoma")

display('==='*10)
display(dict(zip(list(l_Angiomyolipoma_draw),[list(l_Angiomyolipoma_draw).count(i) for i in list(l_Angiomyolipoma_draw)])))
display('==='*10)

sns.set_style('darkgrid')
sns.countplot(l_Angiomyolipoma_draw)

from sklearn.metrics import roc_auc_score
from sklearn.metrics import roc_curve, auc

print('Training Set Clases')
print(training_set.class_indices)
print('Testing Set Clases')
print(test_set.class_indices)
print("====="*10)
print('\nConfusion Matrix')
print('Classification Report')
target_names = ['Adenoma', 'Angiomyolipoma']

y_labels  = y_Adenoma +y_Angiomyolipoma 
x_results = l_Adenoma_result + l_Angiomyolipoma_result
print(classification_report( y_labels , x_results , target_names=target_names))

acc = hist.history['accuracy']
val_acc = hist.history['val_accuracy']
loss = hist.history['loss']
val_loss = hist.history['val_loss']

plt.figure(figsize=(15, 15))
plt.subplot(2, 2, 1)
plt.plot( acc, label='Training Accuracy')
plt.plot( val_acc, label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title('Training and Validation Accuracy')

plt.subplot(2, 2, 2)
plt.plot( loss, label='Training Loss')
plt.plot( val_loss, label='Validation Loss')
plt.legend(loc='upper right')
plt.title('Training and Validation Loss')
plt.show()