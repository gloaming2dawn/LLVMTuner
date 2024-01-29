# -*- coding: utf-8 -*-
"""
Created on Thu Mar  2 17:45:23 2023

@author: jiayu
"""
from multiprocessing import Pool
from array import array
from collections.abc import Mapping, Iterable
from operator import itemgetter
from numbers import Number

import numpy as np
import scipy.sparse as sp




class DictVectorizer:
    _parameter_constraints: dict = {
        "dtype": "no_validation",  # validation delegated to numpy,
        "separator": [str],
        "sparse": ["boolean"],
        "sort": ["boolean"],
    }

    def __init__(self, *, dtype=np.float64, separator="=", sparse=False, sort=True):
        self.dtype = dtype
        self.separator = separator
        self.sparse = sparse
        self.sort = sort


    def fit(self, X, y=None):
        """Learn a list of feature name -> indices mappings.
        Parameters
        ----------
        X : Mapping or iterable over Mappings
            Dict(s) or Mapping(s) from feature names (arbitrary Python
            objects) to feature values (strings or convertible to dtype).
            .. versionchanged:: 0.24
               Accepts multiple string values for one categorical feature.
        y : (ignored)
            Ignored parameter.
        Returns
        -------
        self : object
            DictVectorizer class instance.
        """
        feature_names = list(set().union(*X))
        feature_names.sort()
        vocab = {f: i for i, f in enumerate(feature_names)}

        self.feature_names_ = feature_names
        self.vocabulary_ = vocab

        return self
    
    def single_transform(self, x):
        feature_names = self.feature_names_
        vocab = self.vocabulary_
        vector = np.zeros(len(feature_names))
        for f,v in x.items():
            vector[vocab[f]]=v
        return vector
    
    
    def transform(self, X):
        """Transform feature->value dicts to array or sparse matrix.
        Named features not encountered during fit or fit_transform will be
        silently ignored.
        Parameters
        ----------
        X : Mapping or iterable over Mappings of shape (n_samples,)
            Dict(s) or Mapping(s) from feature names (arbitrary Python
            objects) to feature values (strings or convertible to dtype).
        Returns
        -------
        Xa : {array, sparse matrix}
            Feature vectors; always 2-d.
        """
        
        with Pool() as p:
            vector_list = p.map(self.single_transform, X)
        return vector_list


    def get_feature_names_out(self, input_features=None):
        """Get output feature names for transformation.
        Parameters
        ----------
        input_features : array-like of str or None, default=None
            Not used, present here for API consistency by convention.
        Returns
        -------
        feature_names_out : ndarray of str objects
            Transformed feature names.
        """
        if any(not isinstance(name, str) for name in self.feature_names_):
            feature_names = [str(name) for name in self.feature_names_]
        else:
            feature_names = self.feature_names_
        return np.asarray(feature_names, dtype=object)
