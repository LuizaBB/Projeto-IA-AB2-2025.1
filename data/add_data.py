import pandas as pd
import csv

def readPlates(index):
    infoList = []
    for i in range(0, index):
        info = input(f"Insira informação {i}/{index}: ")
        infoList.append(info)
    return infoList

inputFile = input("Arquivo que se quer adicionar informação: ")
# print(filePath) #print de teste
inputIndex = 0
if inputFile == "pratos.csv":
    inputIndex = 6
else:
    inputIndex = 7
newInfo = readPlates(inputIndex)
print(newInfo) #print de teste
with open(inputFile, mode = 'a', newline = '', encoding = 'utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(newInfo)
print("Dados adicionados com sucesso.")
print(pd.read_csv(inputFile, sep = ','))

#OBS: Funciona quando o ultimo caractere do csv é o \n
    #se isso estiver funcionando todo o resto é adicionado de forma correta