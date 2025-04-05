import nltk
import os

# Set NLTK data path to the virtual environment
nltk_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'nltk_data')
os.makedirs(nltk_data_dir, exist_ok=True)
nltk.data.path.append(nltk_data_dir)

# Download required NLTK data
nltk.download('punkt', download_dir=nltk_data_dir)
nltk.download('stopwords', download_dir=nltk_data_dir)
nltk.download('punkt_tab', download_dir=nltk_data_dir)
