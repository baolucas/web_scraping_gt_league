# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 10:14:55 2020

@author: lucas.gloria
"""

import time
import requests
import pandas as pd
import numpy as np
import math

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import sys

import json

url = "https://gtleagues.com/sports-tree/sports"

def ganhador(home,away,home_goal,away_goal):
    winner = ''
    if home_goal > away_goal:
        winner = home
    elif home_goal < away_goal:
         winner = away
    else:
         winner = "empate"
    
    return winner  

def tot_gols(home_goal,away_goal):
    gols = 0
    gols = home_goal+away_goal
    
    return gols  

def jogadores(home,away):
    jogadores = ''
    jogadores = home+' '+away    
    return jogadores 

def btts(home_goal,away_goal):

    if home_goal >0 and away_goal> 0:
        btts = True
    else:
        btts = False
    
    return btts 


def tratar_df(df):
    
    df_fim = df.copy()


    df_fim["home_goal"] = pd.to_numeric(df_fim["home_goal"]) 
    df_fim['home_goal'] = df_fim['home_goal'].fillna(0)
    df_fim['home_goal'] = df_fim['home_goal'].apply(lambda x: int(x))
    
    df_fim["away_goal"] = pd.to_numeric(df_fim["away_goal"])
    df_fim['away_goal'] = df_fim['away_goal'].fillna(0)
    df_fim['away_goal'] = df_fim['away_goal'].apply(lambda x: int(x))
    
    df_fim["winner_team"] = df_fim.apply(lambda x: ganhador(x["home_team"],x["away_team"],x["home_goal"],x["away_goal"]), axis= 1)
    df_fim["winner_player"] = df_fim.apply(lambda x: ganhador(x["home_player"],x["away_player"],x["home_goal"],x["away_goal"]), axis= 1)
    df_fim['Total de gols'] = df_fim.apply(lambda x: tot_gols(x["home_goal"],x["away_goal"]), axis= 1)
    df_fim['jogadores'] = df_fim.apply(lambda x: jogadores(x["home_player"],x["away_player"]), axis= 1)
    df_fim['btts'] = df_fim.apply(lambda x: btts(x["home_goal"],x["away_goal"]), axis= 1)

    df_fim.drop_duplicates(inplace=True)

    ## coluna confrontos players unicos
    df_fim["id"] = df_fim.index + 1

    temp = df_fim[['home_player','away_player']].copy()
    x = pd.DataFrame(np.sort(temp, axis=1), temp.index, temp.columns)
    x['id'] = x.index + 1
    x['confronto'] = x['home_player'] + ' x ' + x['away_player']

    df_fim = df_fim.merge(x[['id','confronto']], left_on='id', right_on='id')

    df_fim.drop('id',axis=1,inplace=True)


    ## coluna confrontos times unicos
    df_fim["id"] = df_fim.index + 1

    temp = df_fim[['home_team','away_team']].copy()
    x = pd.DataFrame(np.sort(temp, axis=1), temp.index, temp.columns)
    x['id'] = x.index + 1
    x['confronto_times'] = x['home_team'] + ' x ' + x['away_team']

    df_fim = df_fim.merge(x[['id','confronto_times']], left_on='id', right_on='id')

    df_fim.drop_duplicates(inplace=True)
    
    df_fim['jogador1'] = df_fim['confronto'].apply(lambda x : x.split('x')[0].strip())
    df_fim['jogador2'] = df_fim['confronto'].apply(lambda x : x.split('x')[1].strip())
    
    df_fim['Btts_valor'] = df_fim['btts'].apply(lambda x : 1 if x == True else 0 )
    df_fim['Gols Dif Vitoria'] = df_fim.apply(lambda x : abs(x['home_goal'] - x['away_goal']) , axis = 1)
    
    df_fim['Sessao'] = df_fim['Sessao'].apply(lambda x : x.replace(':','').replace(' - ',' ').replace(' ','_').strip())
    df_fim['confronto'] = df_fim['confronto'].apply(lambda x: x.lower())
    df_fim.drop(columns=['id'],inplace=True)
    

    
    return df_fim



def categoria_to_tournaments(driver):
    time.sleep(2)
    elements = driver.find_elements_by_xpath("//table[@class = 'MuiTable-root']/tbody[@class = 'MuiTableBody-root']/tr[@index = 0]/td/a[contains(@class,'MuiTypography')]")
    elements[0].click()
    
    #set value rows page to 100 na página dos torneios ja disputados
    time.sleep(5)
    elements = driver.find_elements_by_xpath("//table[@class='MuiTable-root']/tfoot/tr/td/div/div[contains(@class,'MuiInputBase')]")
    elements[0].click()
    time.sleep(5)
    elements = driver.find_elements_by_xpath("//ul[contains(@class,'MuiList-root')]/li[@data-value='100']")
    elements[0].click()
    time.sleep(5)


def torneios_to_seasons(driver,torneio):
    
    ##COLETA TODAS OS CAMEPONATOS Q TIVERAM. Colocar em loop
    torneios = driver.find_elements_by_xpath("//tbody/tr/td/a/div")
    driver.execute_script("arguments[0].click();", torneios[torneio])   #o numero em torneios indica o click * -1 é o atual
    time.sleep(2)
    

def seasons_to_leagues(driver,liga):
    ### dentro de cada sessão/campeonato, tem as ligas (A,B,C). Tbm em loop dentro do loop
    ligas = driver.find_elements_by_xpath("//tbody[@class='MuiTableBody-root']/tr/td/a")
    time.sleep(1)
    ligas[liga].click() ### aqui define o clique na liga A , B , C ....
    time.sleep(2)

    ##clica em results
    driver.find_elements_by_xpath("//button[@id='simple-tab-1']")[0].click()
    
    ### define para 100 registros em tela
    time.sleep(2)
    elements = driver.find_elements_by_xpath("//table[@class='MuiTable-root']/tfoot/tr/td/div/div[contains(@class,'MuiInputBase')]")
    elements[0].click()
    time.sleep(1)
    elements = driver.find_elements_by_xpath("//ul[contains(@class,'MuiList-root')]/li[@data-value='100']")
    elements[0].click()
    time.sleep(2)
    
def coleta_tabela(driver,pag):
    ##coleta o header da pagina para coletar info gerais como liga, data e etc
    informacoes_gerais = driver.find_elements_by_xpath('//li[@class="MuiBreadcrumbs-li"]')

    list_info_gerais = []
    for i in informacoes_gerais:
        list_info_gerais.append(i.text)

    aux = 1
    list_fim = []
    while aux <= pag:

        print('loop ',aux)
        ###coletar informações da tabela com os jogos
        tabela = driver.find_elements_by_xpath("//div[@class='jss14']/div/div/div/table")


        conteudo = tabela[0].get_attribute('outerHTML')

        soup = BeautifulSoup(conteudo,'html.parser')
        table= soup.find(name = 'table')
        df_full = pd.read_html(str(table))[0]

        temp = 0

        for i in range(len(soup.findAll('tr'))):
            list_aux = []
            if "MuiTableRow-hover" in soup.findAll('tr')[i]['class']:

                for y in range(len(soup.findAll('tr')[i].findAll('td'))):
                    if soup.findAll('tr')[i].findAll('td')[y].has_attr('value') == True:
                        #print(soup.findAll('tr')[i].findAll('td')[y]['value'])
                        list_aux.append(soup.findAll('tr')[i].findAll('td')[y]['value'])
                    else:
                        list_aux.append('')

                    if len(soup.findAll('tr')[i].findAll('td')[y].findAll('div')) > 0:
                        if soup.findAll('tr')[i].findAll('td')[y].findAll('div')[0].find('div') is not None and y < 10:
                            list_aux.append(soup.findAll('tr')[i].findAll('td')[y].findAll('div')[0].find('div').find('input')['value'])
                list_fim.append(list_info_gerais + list_aux)

        if aux < pag:
            next_page = driver.find_elements_by_xpath('//div[@class="MuiToolbar-root MuiToolbar-regular MuiTablePagination-toolbar jss4 MuiToolbar-gutters"]/div[@class="jss16"]/span[@title="Next Page"]/button')
            time.sleep(2)
            driver.execute_script("arguments[0].click();",next_page[0])
            #next_page[0].click()
        aux = aux + 1 #executa o loop no numero de paginas
        time.sleep(5)
        
    df = pd.DataFrame(list_fim)
    return df


def main(argv):
    
    #while True:
	argv = int(argv)
	if argv == 0: 
		print('League A')
	elif argv == 1:
		print('League B')
	elif argv == 2:
		print('League C')
	else: 
		print('Nada')
  
	option = Options()
	option.headless = True
	#option.binary = 'binary'
	driver = webdriver.Chrome()
	driver.get(url)
	time.sleep(5)

	#procura e realiza o click para ir para a tela de categoria
	elements = driver.find_elements_by_xpath("//td[contains(@class,'MuiTable')]/a[contains(@class,'MuiTypography')]")
	elements[1].click()

	time.sleep(2)

	categoria_to_tournaments(driver)

	##COLETA TODAS OS CAMEPONATOS Q TIVERAM. Colocar em loop
	torneios_to_seasons(driver,-1)
	seasons_to_leagues(driver,argv)

	## verifica quantas paginas possui após mudar a visão para 100
	paginas = driver.find_elements_by_xpath('//span[@class="MuiTypography-root MuiTypography-caption"]')
	#pag = round(int(paginas[0].text.split('of')[1].strip())/100)
	pag = math.ceil(int(paginas[0].text.split('of')[1].strip())/100)

	df_tabela_dados = coleta_tabela(driver,pag)
	now = datetime.now()
	date_time = now.strftime("%m_%d_%Y_%H_%M_%S")
	df_tabela_dados.rename({0:'Categoria',1:'FIFA',2:'GT',3:'Sessao',4:'Liga',5:'pendente',6:'id_jogo_sessao',7:'week',
							 8:'data_hora',9:'home_player',10:'away_player',11:'home_team',12:'away_team',13:'pendente2',
							 14:'home_goal',15:'pendente3',16:'away_goal',
							 17:'status_game'},axis =1, inplace=True)

	driver.quit()

	if len(df_tabela_dados) > 2:
		df_final = tratar_df(df_tabela_dados)
		torneio = df_final.iloc[3][3].replace(':','').strip()
		torneio = torneio.replace(' ','_')
		liga = df_final.iloc[3][4]
		df_final.to_csv('df_'+torneio+liga+'.csv', mode='a', index = None, header=None,sep = ';')
		print(torneio, liga)

		# use creds to create a client to interact with the Google Drive API
		scope = ['https://spreadsheets.google.com/feeds',
				 'https://www.googleapis.com/auth/drive']
		creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_JSON_CREDENCIAL_GOOGLE_SHEETS, scope)
		
		client = gspread.authorize(creds)
		sheet = client.open("gt_league_results").sheet1
		list_of_hashes = sheet.get_all_records()
		df_dados = pd.DataFrame(list_of_hashes)
		
		result = pd.merge(df_final,
				 df_dados[['data_hora', 'confronto','Liga','status_game']],
				 on=['data_hora', 'confronto','Liga'], 
				 how='left')
		
		result = result[result.status_game_y.isna()] #verifica as linhas novas
		if len(result) > 0:
			result.drop(columns=['status_game_y'],inplace=True)
			result.rename({'status_game_x':'status_game'},axis =1, inplace=True)
			set_with_dataframe(sheet, result,row=len(df_dados)+2,include_column_header=False) #insere no sheets
			print('Linhas inseridas')
		else:
			print('Sem linhas para inserir')
		
	print('Fim desse loop as ', now.strftime("%m_%d_%Y_%H_%M_%S"))
        #time.sleep(1800)

if __name__ == "__main__":
    #print(sys.argv[1])
    main(sys.argv[1])
