import os
import pandas as pd
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = genai.Client()

def load_data():
    try:
        global df_pratos, df_vinhos
        df_pratos = pd.read_csv('data/pratos.csv')
        df_vinhos = pd.read_csv('data/vinhos.csv')
        print("Dados carregados com sucesso.")
    except FileNotFoundError as e:
        print(f"Erro ao carregar dados: Verifique se os arquivos CSV estão na pasta 'data'. Erro: {e}")
        exit()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_dish_description = request.form.get('dish_input')
        recommended_wine = "Aguardando Algoritmo..."
        justification = "Aguardando Justificativa do Gemini..."
        return render_template('index.html', recommendation=recommended_wine, justification=justification,dish_input=user_dish_description)
    return render_template('index.html')

if __name__ == '__main__':
    load_data()
    app.run(debug=True) #bom para desenolvimento, desativar em produção