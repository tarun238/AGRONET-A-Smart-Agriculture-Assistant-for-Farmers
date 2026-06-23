import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn import linear_model
import os
def check_stat(File):
    

    # Split the filename using dot as delimiter
    namee = File.split(".")

    # Extract the filename without extension
    crop_n = namee[0]
    try:
        os.remove("static/result_stats.png")
    except:
        print("Graph Already Deleted or permssion Error")
    # Load the dataset
    df = pd.read_csv(f"datas//{File}")

    # Convert 'Price Date' to datetime
    df['pricedate'] = pd.to_datetime(df['pricedate'])

    # Extracting and renaming the important variables
    df['Mean'] = (df['minprice'] + df['maxprice']) / 2

    # Cleaning the data for any NaN or Null fields
    df = df.dropna()

    # Creating a copy for making small changes
    dataset_for_prediction = df.copy()
    dataset_for_prediction['Actual'] = dataset_for_prediction['Mean'].shift()
    dataset_for_prediction = dataset_for_prediction.dropna()

    # N--> train size
    N = 2441

    # Prediction mean based upon min price
    X = df['minprice']
    X = np.array(X)
    X = np.array(X, dtype='float32')
    Xtrain = X[:N]

    # Creating test data
    Xtest = X[-272:]
    Y = df['Mean']
    Y = np.array(Y, dtype='float32')
    ytrain = Y[:N]
    ytest = Y[-272:]
    arr = ytest

    # Load BayesianRegression from sklearn
    reg = linear_model.BayesianRidge()
    reg.fit(Xtrain.reshape((len(Xtrain), 1)), ytrain)
    ypred = reg.predict(Xtest.reshape((len(Xtest), 1)))
    ytest = ytest.reshape((272, 1))

    # Plot the same
    plt.plot(arr, label='actual')
    plt.plot(ypred, label='predicted')
    plt.xlabel('Days')
    plt.ylabel('Prices')
    plt.title(f'Time Series for {crop_n}')
    plt.legend()
    plt.savefig("static/result_stats.png")
    plt.close()
    # # Report the RMSE
    # c = 0
    # for i in range(272):
    #     c += (ypred[i] - ytest[i]) ** 2
    # c /= 272
    # print("RMSE:", c ** 0.5)

    # print("BAYESIAN REGRESSION")
    # print("Mean value depending on min price")

