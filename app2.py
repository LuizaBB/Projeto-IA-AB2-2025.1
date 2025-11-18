import os
import pandas as pd
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

from google.genai.errors import APIError
import json

import time

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
    MAX_RETRIES = 3
    DELAY_SECONDS = 2
    for attempt in range(MAX_RETRIES):
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
            if attempt < MAX_RETRIES - 1:
                    print(f"Erro na API Gemini (Tentativa {attempt + 1}): {e}. Tentando novamente em {DELAY_SECONDS}s...")
                    time.sleep(DELAY_SECONDS)
            else: #especifico para ultima falha
                print(f"Erro na API Gemini: Falha após {MAX_RETRIES} tentativas. Erro: {e}")
                return {}
        except Exception as e:
            print(f"Erro inesperado no processamento do JSON: {e}")
            return {}
    return {}

def recommend_wine(dish_features: dict, df_vinhos: pd.DataFrame) -> tuple[str, int]:
    tipo_carne = dish_features.get('tipo_carne', 'Não Classificado')
    intensidade = dish_features.get('intensidade', 3)
    acidez_prato = dish_features.get('acidez', 'Média')
    scored_df = df_vinhos.copy()
    scored_df['score'] = 0
    if tipo_carne == 'Carne Vermelha':
        scored_df['score'] += scored_df['tipo'].apply(lambda x: 30 if x == 'Tinto' else 5)
    elif tipo_carne in ['Peixe', 'Aves']:
        scored_df['score'] += scored_df.apply(lambda row: 30 if row['tipo'] in ['Branco', 'Rosé'] else (15 if row['corpo'] == 'Leve' else 0), axis=1)
    elif tipo_carne == 'Vegetariano':
        scored_df['score'] += scored_df.apply(lambda row: 30 if (row['tipo'] in ['Branco', 'Rosé'] or 'terra' in row['notas_sabor']) else 0, axis=1)
    if intensidade >= 4:
        scored_df['score'] += scored_df['corpo'].apply(lambda x: 50 if x == 'Encorpado' else (25 if x == 'Médio' else 0))
    elif intensidade <= 2:
        scored_df['score'] += scored_df['corpo'].apply(lambda x: 50 if x == 'Leve' else (25 if x == 'Médio' else 0))
    else:
        scored_df['score'] += scored_df['corpo'].apply(lambda x: 50 if x == 'Médio' else 25)
    if acidez_prato == 'Alta':
        scored_df['score'] += scored_df['acidez'].apply(lambda x: 20 if x in ['Média', 'Alta'] else 0)
    elif acidez_prato == 'Baixa':
        scored_df['score'] += scored_df['acidez'].apply(lambda x: 20 if x in ['Baixa', 'Média'] else 0)
    scored_df = scored_df[scored_df['score'] > 0] #inicio da selecao final
    if scored_df.empty:
        return "Pinot Noir (Recomendação Padrão)", 50
    best_match = scored_df.loc[scored_df['score'].idxmax()]
    return best_match['vinho_nome'], int(best_match['score'])

def generate_justification(client: genai.Client, dish_description: str, wine_name: str, df_vinhos: pd.DataFrame, wine_score: int) -> str:
    try:
        wine_data = df_vinhos[df_vinhos['vinho_nome'] == wine_name].iloc[0]
        notas_sabor = wine_data['notas_sabor']
        tipo_vinho = wine_data['tipo']
        corpo_vinho = wine_data['corpo']
    except IndexError:
        return f"Não foi possível encontrar detalhes para o vinho {wine_name} para justificar."
    prompt = f"""
    Você é um sommelier especialista. Sua tarefa é escrever uma justificativa de harmonização de vinhos de forma persuasiva e elegante.

    - **PRATO:** {dish_description}
    - **VINHO RECOMENDADO:** {wine_name} ({tipo_vinho}, {corpo_vinho})
    - **COMPATIBILIDADE CALCULADA:** {wine_score}%
    - **CARACTERÍSTICAS-CHAVE DO VINHO:** Notas de {notas_sabor}.

    Explique a harmonização em 3 a 4 frases, usando o percentual de compatibilidade para reforçar a excelência da escolha. Foque em como as características do vinho (corpo, notas, acidez) se complementam ou contrastam com as características do prato, elevando a experiência gastronômica.
    """
    MAX_RETRIES = 3
    DELAY_SECONDS = 2
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt)
            return response.text
        except APIError as e:
            if attempt < MAX_RETRIES - 1:
                print(f"Erro na justificativa (Tentativa {attempt + 1}): {e}. Tentando novamente em {DELAY_SECONDS}s...")
                time.sleep(DELAY_SECONDS)
            else: #especifico para a ultima tentativa
                print(f"Erro na API Gemini: Falha na Geração de Justificativa após {MAX_RETRIES} tentativas. Erro: {e}")
                return "Erro: O servidor de Inteligência Artificial está temporariamente indisponível. Por favor, tente novamente mais tarde."
    return "Erro desconhecido. Não foi possível gerar a justificativa."

@app.route('/', methods=['GET', 'POST'])

def index2():
    global client, df_vinhos
    if request.method == 'POST':
        text_description = request.form.get('dish_input', '').strip() 
        selected_ingredients = request.form.getlist('main_ingredient')
        if text_description:
            user_dish_description = text_description
        elif selected_ingredients: #usar checkbox se caixa de texto estiver vazia
            ingredients_str = ", ".join(selected_ingredients)
            user_dish_description = f"Prato principal com os ingredientes: {ingredients_str}."
        else:
            return render_template('index1.html', recommendation="Por favor, descreva o prato ou selecione ingredientes.", justification="")
        dish_features = extract_dish_characteristics(client, user_dish_description)
        if not dish_features:
             return render_template('index2.html', recommendation="Erro: Não foi possível processar o prato. Tente novamente.", justification="")
        recommended_wine, wine_score = recommend_wine(dish_features, df_vinhos)
        justification = generate_justification(client, user_dish_description, recommended_wine, df_vinhos, wine_score)
        return render_template('index2.html', recommendation=recommended_wine, justification=justification, dish_input=text_description, wine_score=wine_score)
        #dish_input: se tiver, é usado, se não passa como None
    return render_template('index2.html') #metodo GET

if __name__ == '__main__':
    load_data()
    app.run(debug=True) #bom para desenvolvimento, desativar em produção