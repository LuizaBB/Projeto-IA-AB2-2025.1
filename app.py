import os
import pandas as pd
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

from google.genai.errors import APIError
import json

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

def extract_dish_characteristics(client: genai.Client, dish_description: str) -> dict:
    prompt = f"""
    Analise a descrição do prato abaixo e extraia as seguintes características em um objeto JSON: 
    'tipo_carne' (ex: 'Carne Vermelha', 'Peixe', 'Aves', 'Vegetariano'),
    'intensidade' (Um número de 1 a 5, onde 1 é muito leve e 5 é muito forte/encorpado),
    'acidez' (ex: 'Baixa', 'Média', 'Alta'),
    'sabor_principal' (ex: 'Doce', 'Salgado', 'Picante', 'Terroso').

    Descrição do Prato: "{dish_description}"
    """ #prompt detalhado para o gemini
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=genai.types.GenerateContentConfig(
            response_mime_type="application/json", 
                response_schema={
                    "type": "object",
                    "properties": {
                        "tipo_carne": {"type": "string"},
                        "intensidade": {"type": "number"},
                        "acidez": {"type": "string"},
                        "sabor_principal": {"type": "string"}}}))
        return json.loads(response.text)
    except APIError as e:
        print(f"Erro na chamada da API Gemini: {e}")
        return {}
    except Exception as e:
        print(f"Erro inesperado no processamento do JSON: {e}")
        return {}
    
def recommend_wine(dish_features: dict, df_vinhos: pd.DataFrame) -> str:
    tipo_carne = dish_features.get('tipo_carne', 'Não Classificado')
    intensidade = dish_features.get('intensidade', 3)
    acidez_prato = dish_features.get('acidez', 'Média')
    recommended_df = df_vinhos.copy()
    if tipo_carne == 'Carne Vermelha':
        recommended_df = recommended_df[recommended_df['tipo'] == 'Tinto']
    elif tipo_carne in ['Peixe', 'Aves']:
        recommended_df = recommended_df[
            (recommended_df['tipo'].isin(['Branco', 'Rosé'])) | (recommended_df['corpo'] == 'Leve')]
    elif tipo_carne == 'Vegetariano':
        recommended_df = recommended_df[
            (recommended_df['notas_sabor'].str.contains('terra|cogumelo', case=False, na=False)) | (recommended_df['tipo'].isin(['Branco', 'Rosé']))]
    if intensidade >= 4:
        recommended_df = recommended_df[recommended_df['corpo'] == 'Encorpado']
    elif intensidade <= 2:
        recommended_df = recommended_df[recommended_df['corpo'] == 'Leve']
    if acidez_prato == 'Alta':
        recommended_df = recommended_df[recommended_df['acidez'].isin(['Média', 'Alta'])]
    elif acidez_prato == 'Baixa' and recommended_df['tipo'].iloc[0] == 'Branco':
        recommended_df = recommended_df[recommended_df['acidez'].isin(['Baixa', 'Média'])]
    if recommended_df.empty:
        return "Pinot Noir (Recomendação Padrão por Versatilidade)"
    return recommended_df['vinho_nome'].iloc[0]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_dish_description = request.form.get('dish_input')
        recommended_wine = "Aguardando Algoritmo..."
        justification = "Aguardando Justificativa do Gemini..."
        return render_template('index1.html', recommendation=recommended_wine, justification=justification,dish_input=user_dish_description)
    return render_template('index1.html')

if __name__ == '__main__':
    load_data()
    app.run(debug=True) #bom para desenvolvimento, desativar em produção