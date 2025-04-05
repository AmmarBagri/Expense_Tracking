# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk
import json
from rest_framework.permissions import IsAuthenticated 
from .serializers import YourDataSerializer
import pickle
import os

# Initialize the model and vectorizer as global variables
model = None
tfidf_vectorizer = None

def load_or_train_model():
    global model, tfidf_vectorizer
    
    try:
        # Try to load existing model and vectorizer
        data = pd.read_csv('dataset.csv')
        
        if os.path.exists('model.pkl') and os.path.exists('vectorizer.pkl'):
            with open('model.pkl', 'rb') as f:
                model = pickle.load(f)
            with open('vectorizer.pkl', 'rb') as f:
                tfidf_vectorizer = pickle.load(f)
        else:
            # Train new model and vectorizer
            tfidf_vectorizer = TfidfVectorizer(min_df=1)
            X = tfidf_vectorizer.fit_transform(data['clean_description'])
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X, data['category'])
            
            # Save the model and vectorizer
            with open('model.pkl', 'wb') as f:
                pickle.dump(model, f)
            with open('vectorizer.pkl', 'wb') as f:
                pickle.dump(tfidf_vectorizer, f)
                
    except Exception as e:
        print(f"Error in load_or_train_model: {str(e)}")
        return None

# Load the model at startup
load_or_train_model()

class PredictCategory(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_input = request.data.get('description', '')
            if not user_input:
                return Response({'error': 'Description is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Preprocess the input
            processed_input = preprocess_text(user_input)
            
            # Transform the input using the loaded vectorizer
            user_input_vector = tfidf_vectorizer.transform([processed_input])
            
            # Make prediction
            predicted_category = model.predict(user_input_vector)[0]
            
            return Response({'predicted_category': predicted_category}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateDataset(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            new_data = request.data.get('new_data')
            if not new_data or 'description' not in new_data or 'category' not in new_data:
                return Response({'error': 'Invalid data format'}, status=status.HTTP_400_BAD_REQUEST)

            # Load existing dataset
            data = pd.read_csv('dataset.csv')
            
            # Prepare new data
            new_description = new_data['description']
            new_category = new_data['category']
            clean_description = preprocess_text(new_description)
            
            # Add new data
            new_row = {
                'description': new_description,
                'category': new_category,
                'clean_description': clean_description
            }
            data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
            
            # Save updated dataset
            data.to_csv('dataset.csv', index=False)
            
            # Retrain the model
            load_or_train_model()
            
            return Response({'message': 'Dataset updated and model retrained'}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def preprocess_text(text):
    try:
        stop_words = set(stopwords.words('english'))
        tokens = word_tokenize(str(text).lower())
        tokens = [t for t in tokens if t.isalnum() and t not in stop_words]
        return ' '.join(tokens)
    except Exception as e:
        print(f"Error in preprocess_text: {str(e)}")
        return str(text).lower()  # Fallback to basic preprocessing
