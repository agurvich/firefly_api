
import numpy as np
import pandas as pd
import os

def clean_dictionary(dictionary):

    ## if using pandas we don't need to clean any dictionaries
    return dictionary 
    temp_dictionary = {}


    convert_to_list = False
    convert_to_tuple = type(dictionary) == tuple
    if type(dictionary) != dict:
        dictionary = dict(zip(range(len(dictionary)),dictionary))
        convert_to_list = True

    for key in dictionary:

        value = dictionary[key]

        ## check if the value is an array
        if type(value) == np.ndarray:
            value = value.tolist()
            ## now clean the list itself just in case
            value = clean_dictionary(value)

        ## handle any numpy ints
        elif type(value) in [np.int64,np.int32,np.int16,np.int8]:
            value = int(value)
        
        ## handle nested dictionaries or lists
        elif type(value) == dict or type(value) == list or type(value) == tuple:
            value = clean_dictionary(value)
        
        temp_dictionary[key] = value

    if convert_to_list:
        temp_dictionary = [temp_dictionary[key] for key in temp_dictionary]
    if convert_to_tuple:
        if not convert_to_list:
            raise RuntimeError(
                "Something didn't go correctly in cleaning the dictionary.",
                dictionary)
        temp_dictionary = tuple(temp_dictionary)


    return temp_dictionary

def write_to_json(dictionary,path):
    return_value = pd.Series(dictionary)
    return_value.to_json(path,orient='index')
    return return_value

def load_from_json(path):
    if os.path.isfile(path):
        with open(path,'r') as handle:
            dictionary=pd.io.json.loads(''.join(handle.readlines()))
    return dictionary
        
    