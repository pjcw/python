import tkinter as tk
import threading
import time
import pandas as pd
import pandas_ta as ta
import datetime
import schedule
import ccxt
import json
import websockets
import sys
import math
import csv
import asyncio 
import traceback
from colorama import Fore, Style
import random
from IndicadorPlotter import IndicatorPlotter
# from indicadorPlotterplty import IndicatorPlotter

# Variáveis globais
versao = " - 5.3"
quem_entra = None
boxes_and_labels = {}  # referenciar boxea de trades abertos.
log_box = None
estrat = None
last_timestamp = {}
running = True
open_trades_box = None
balance_label = None
open_trades = {}
df_abertos = {}   # para manter o data frame que foi aberto em algum trade
closed_trades = []
max_trades = 20
trade_size = 100  # Tamanho do trade em dólares, por exemplo
total_trades_count = 0
long_trades_count = 0
short_trades_count = 0
closed_trades_count = 0
trade_size_entry = None
trades_2_remove = []
balance = None
black_list = []
subscriptions= {}
usdt_markets = []
vol_lucro = 0
vol_preju = 0
lev = 20
tf = '15'
precisao = 0
direction_map = {
    'long': ('buy', 'sell'),
    'short': ('sell', 'buy')
}
params = {'type': 'future'}
ativo = True
current_balance = 0
# Parâmetros do trailing stop
trailing_stop_percent = 0.02  # 2%   Para experimentar sugestão do chatGPT pra trailing stop


# Credenciais da Binance (substitua pelos seus próprios valores)
api_key = "hDbrvDLYCnTDLNOUsVrkJ3K3RCHhItrgaFWw7NOSgE75DMrpMtztWsZqS3v2eP6G"
secret = "2JmABrFZpJJIx2uPk8NhzXyTe4MpmeTsgP7c5grLkZWLQNqN1nxLdzc9gXBOquvs"
# API Testnet Binance
#api_key: "eqfHvh9DvYzSujV1B7uSZ9PelsrebNtccAENqFRGNBFjSfKuqXLYeftD2MqssXrR"
#secret: "NbDHdROF1FzpGtNWoh14D9PnYXYN6I7SXIBXEgkUHpviHbTowMCFFbp9pVwnAzEm"

# Configuração da Binance usando ccxt
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret,
    'options': {
        'defaultType': 'future',  # Configura para utilizar a API de futuros
    },
})
# Endpoint WebSocket da Binance
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"
#  função para escrever o arquivo de trades no fim do processamento
def datetime_to_str(dt):
    if dt is None:
        return ''
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# Função WebSocket para monitorar dados em tempo real
"""async def binance_websocket(symbol,order_id = None):
    uri = f"{BINANCE_WS_URL}/{symbol}@ticker"  # Subscrição ao stream de trades
    async with websockets.connect(symbol_uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            price = float(data['p'])
            print(f"{Fore.LIGHTBLUE_EX}Novo trade para {symbol.upper()} - Preço: {price}{Style.RESET_ALL}")"""

async def subscribe_to_ticker(symbol):
    uri = f"wss://stream.binance.com:9443/ws/{symbol}@ticker"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"valor de {symbol} = {data['p']}")

async def unsubscribe_from_ticker(symbol):
    uri = f"wss://stream.binance.com:9443/ws"
    async with websockets.connect(uri) as websocket:
        unsubscribe_message = {"type": "unsubscribe", "symbol": f"{symbol}@ticker"}
        await websocket.send(json.dumps(unsubscribe_message))
        print(f"Subscrição para {symbol} cancelada.")

# Escrever no arquivo CSV
def escrvcsv(trade_data):
    csv_filename = f'trade_log.csv'
    # Cabeçalhos do CSV
    headers = ['symbol', 'direction', 'timestamp', 'timestamp_close', 'open_price', 'amount', 'close_price', 
            'valor_da_compra', 'stop_loss', 'stop_gain', 'initialWallet', 'reazon']
    with open(csv_filename, mode='w', newline='') as csvfile:

        writer = csv.DictWriter(csvfile, fieldnames=headers)

        # Escreve o cabeçalho
        writer.writeheader()

        # Escreve os dados
        for trade in trade_data.keys():
            # Converte datetime para string
            print(f'trade : {trade_data[trade]}  :')

            #trade['timestamp'] = datetime_to_str(trade['timestamp'])
            # trade['timestamp_close'] = datetime_to_str(trade['timestamp_close'])

            writer.writerow(trade_data[trade])
            
def escrever_market(market):
    csv_filename = f'markets.csv'
    # Cabeçalhos do CSV
    headers = market.keys()
    with open(csv_filename, mode='w', newline='') as csvfile:

        writer = csv.DictWriter(csvfile, fieldnames=headers)

        # Escreve o cabeçalho
        writer.writeheader()
        writer.writerow(market)
# Função para fechar a janela do GUI
def on_closing():
    global app
    open_trades.clear
    app.destroy()
    app.quit()
    quit()

# Função para obter o saldo real da conta na Binance
def get_account_balance():
    global balance, params, max_trades
    if app.trade_mode.get() == 'REAL':
        balance_info = exchange.fetch_balance(params=params)  # Especificar que é a conta de futuros
        balance = balance_info['free']['USDT']  # Supondo que o saldo está em USDT
    else:
        balance = 1000.00


    return balance

# Função para atualizar o saldo da conta
def update_balance_inicial():
    global balance_label, balance, max_trades
    if app.trade_mode.get() == "REAL":
        balance = get_account_balance()  # Função que obtém o saldo da conta
    else:
        balance = 1000
    app.balance_label.config(text=f"Saldo da Conta: ${balance:.2f}", font=12)
    
    print(f'Max_trades : {max_trades}  balance : {balance} trade_size : {trade_size}')
    # app.balance.value = balance
    #balance_value.config(text=str(balance))

def update_open_trades():
    global open_trades_box, open_trades

    # app.close_trade_box(symbol)
    # open_trades_box.delete(1.0, tk.END)
    
    for symbol, trade in open_trades.items():
        """if trade['direction'] == 'long':
            op_price = (trade['stop_gain'] - trade['open_price'])/trade['open_price']
            sloss = (trade['open_price']-trade['stop_loss'])/trade['open_price']*100
        else:
            op_price =  (trade['open_price'] - trade['stop_gain'])/trade['open_price']
            sloss = (trade['stop_loss']-trade['open_price'])/trade['open_price']*100
        gain = f"{trade['stop_gain']}\n{op_price}"
        loss = f"{trade['stop_loss']}\n{sloss}"
        """
        # app.open_new_trade_box(tk.END, f"{symbol}, {trade['direction']} , {trade['open_price']}, {trade['stop_loss']}, {trade['stop_gain']} , {fetch_current_price(symbol)} \n")
        current_price,timestamp_ticker = fetch_current_price(symbol)
        app.open_new_trade_box(tk.END, f"{symbol}, {trade['direction']} , {trade['open_price']}, {trade['stop_loss']},  {current_price} \n")
    #    app.create_trade_box(symbol, trade['open_price'], trade['stop_loss'])


# Classe TradeBox
class TradeBox(tk.Frame):
    def __init__(self, master, direction, symbol, entry_price, stop_loss, profit, current_price, df, pnl = 0.0):
        super().__init__(master, relief=tk.RAISED, bd=2, width=700)  # Only set width
        self.pack(padx=0, pady=0, fill=tk.X, expand=False)  # Removendo espaçamento
        global df_abertos
        self.symbol = symbol
        self.pnl = pnl 
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.profit = profit
        # self.pnl = (profit * lev * trade_size)/100

        self.current_price = current_price
        self.df = df  # DataFrame correspondente ao símbolo

        self.direcao_label = tk.Label(self, text=f"Direcao: {direction}", font=("Helvetica", 12)) #{current_price:.2f}
        self.direcao_label.pack(side=tk.LEFT, padx=5, pady=2)
        # self.symbol_label = tk.Label(self, text=f"Trade: {symbol}")
        # self.symbol_label.pack(side=tk.LEFT, padx=5, pady=5)
        #   ==== plotagem
        self.symbol_label = tk.Label(self, text=f"Trade: {symbol}")
        self.symbol_label.pack(side=tk.LEFT, padx=5, pady=2)
        self.symbol_label.bind("<Button-1>", self.plot_graph)
        # ========== 
        self.entry_price_label = tk.Label(self, text=f"Entry Price: {entry_price:.6f}")
        self.entry_price_label.pack(side=tk.LEFT, padx=5, pady=2)
        stop_loss_frame = tk.Frame(self)
        stop_loss_frame.pack(side=tk.LEFT, padx=5, pady=2)

        self.take_profit_label = tk.Label(stop_loss_frame, text=f"Take Profit:  {profit:.2f}")
        self.take_profit_label.pack(side=tk.TOP)

        self.stop_loss_label = tk.Label(stop_loss_frame, text=f"Stop Loss: {stop_loss:.6f}")
        self.stop_loss_label.pack(side=tk.TOP)

        self.profit_pnl_frame = tk.Frame(self)
        self.profit_pnl_frame.pack(side=tk.RIGHT, padx=0, pady=0)
        self.pnl_label = tk.Label(self.profit_pnl_frame, text=f"PNL :   {self.pnl:.2f}", font=("Helvetica", 10))
        self.pnl_label.pack(side=tk.TOP, padx=1, pady=1)
        self.profit_label = tk.Label(self.profit_pnl_frame, text=f"Take Profit:   {profit:.2f}")
        self.profit_label.pack(side=tk.BOTTOM, padx=1, pady=1)
        self.current_price_label = tk.Label(self, text=f"Current Price: {current_price:.6f}")
        self.current_price_label.pack(side=tk.LEFT, padx=1, pady=1)

        self.close_button = tk.Button(self, text="Fechar Trade", command=self.close_trade_manually)
        self.close_button.pack(side=tk.RIGHT, padx=1, pady=1)

        self.pack(padx=0, pady=0, fill=tk.X)

    def plot_graph(self, event):
        # Instancia a classe IndicatorPlotter e chama o método para plotar o gráfico
        try:
            ohdf = fetch_ohlcv(self.symbol)
            current_price,timestamp = fetch_current_price(self.symbol)
            #ohdf['timestamp'] = pd.to_datetime(ohdf['timestamp'], unit='ms')
            #ohdf.set_index('timestamp', inplace=True)
            print(f" tipo de indice de ohdf {type(ohdf.index)}")
            ohdf = calc_indicadores(ohdf,current_price,self.symbol)
        except Exception as erro:
            print(f"erro na chamada de plot_graph : {erro}")
        # Renomeando as colunas para a forma esperada pelo mplfinance
        
        # plotter = IndicatorPlotter(pd.concat([ohdf,pd.DataFrame(df_abertos[self.symbol])],axis=1))
        # df_temp = pd.concat([ohdf, df_abertos[self.symbol]], axis=1)
        # print(f"open_trades.column : {open_trades.items()}")
        ohdf = ohdf.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        # print(f'colunas de ohdf : {ohdf.columns}')

        # print(f"conteúdo dos indices de ohdf : {ohdf.Index     index.tail(10)}")
        plotter = IndicatorPlotter(ohdf, open_trades[self.symbol]['open_price'], open_trades[self.symbol]['stop_loss'], open_trades[self.symbol]['stop_gain'],self.symbol, tf, exchange, open_trades[self.symbol]['timestamp'])
        #plotter.plot_real_time()  # Ou o método que você implementou na classe
        plotter.plot()
        


    def close_trade(self):
        global closed_trades_count
        preco_atual,timestamp_ticker =  fetch_current_price(self.symbol)
        # tem que verificar comando abaixo. Não estou certo sobre os parametros ....
        tcl.close_trade(self.symbol,preco_atual, timestamp_ticker)
        
        self.destroy()
# Função para fechar manualmente um trade

    def close_trade_manually(self):

        global open_trades, total_trades_count, closed_trades, closed_trades_count, long_trades_count, short_trades_count, vol_preju, vol_lucro
       
        preco_atual,timestamp_ticker =  fetch_current_price(self.symbol)
        tcl.close_trade(self.symbol, preco_atual, "")
        return
        open_trades[self.symbol]['close_price'] = preco_atual
        trade = open_trades[self.symbol]
        
        trades_2_remove.append(self.symbol)
        df_abertos.pop(self.symbol)
        
        if trade:
            closed_trades[self.symbol] = trade
            if open_trades[self.symbol]['direction']=="long":
                long_trades_count -= 1
            else:
                short_trades_count -=1
            closed_trades_count += 1
            total_trades_count -= 1

    
            # update_open_trades()
            try:
                app.update_counters(self.symbol, total_trades_count, long_trades_count, short_trades_count, closed_trades_count)
            except Exception as e3:
                print(f'Erro ao atualizar contadores: >>>>>>>>>>>>>>>>>>> {e3}')
            #app.update_balance(open_trades[self.symbol]["direction"])
            try:
                # result = self.calculo_update_result()
                #definição das variáveis para facilitar visualização no debug =======
                Q1 = open_trades[self.symbol]["quant"]
                oprice = open_trades[self.symbol]["open_price"]
                cprice = open_trades[self.symbol]["close_price"]
                alav = lev
                direc = open_trades[self.symbol]["direction"]
                
                result = calcular_saldo(Q1,open_trades[self.symbol]["open_price"],open_trades[self.symbol]["close_price"],alav, direc )
                # result -= open_trades[self.symbol]["open_price"]
                # ====================================================================
                val_semtradesiz = result - trade_size
                if val_semtradesiz > 0:
                    vol_lucro += val_semtradesiz
                   # app.trade_c_lucro_label.config(text=str(vol_lucro))
                    app.trade_c_lucro_label.config(
                        text=f"Lucro: {vol_lucro:.2f}",  # Formatando o número com duas casas decimais
                        fg="green",  # Cor da fonte em verde
                        font=("Helvetica", 12, "bold")  # Fonte Helvetica, tamanho 12, negrito
)
                else:
                    vol_preju += val_semtradesiz
                    #app.trade_c_prej_label.config(text=str(vol_preju))
                    app.trade_c_prej_label.config(
                        text=f"Prej: {vol_preju:.2f}",  # Formatando o número com duas casas decimais
                        fg="red",  # Cor da fonte em verde
                        font=("Helvetica", 12, "bold")  # Fonte Helvetica, tamanho 12, negrito
)
                # ==========================================================================
                app.update_balance( self.symbol, open_trades[self.symbol]["direction"], result)
            except Exception as e4:
                print(f'Erro ao executar update balance : {e4} !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            finally:
                app.trade_boxes.pop(self.symbol)
                self.destroy()
    def calculo_update_result(self):
        # Calcula o resultado do trade
        try:
            q = open_trades[self.symbol]['amount']  # pega a quantidade para multiplicar pelo preço atual
            # result = self.entry_price + (self.current_price - self.entry_price) * self.profit
            result = q * (open_trades[self.symbol]['close_price'] - open_trades[self.symbol]['open_price'])
        except Exception as e5:
            print(f'Exceção no calculo de resultado: {e5}')
        # self.result_label.config(text=f"Resultado: {result:.4f}")
        print(f'Result ao fim do calculo: {result}') 
        return result
# Classe TradeManagerApp
class TradeManagerApp(tk.Tk):
    def __init__(self):
        global versao
        super().__init__()
        self.trade_boxes = {}
        self.title(f"Cachorro v{versao}")
        self.geometry("800x800")

        # Frame superior com três caixas alinhadas horizontalmente
        top_frame = tk.Frame(self)
        top_frame.pack(fill='x', pady=10, padx=10)
        cont_frame = tk.Frame(self)
        cont_frame.pack(fill='x', pady=10, padx=10)
        # Caixa para o saldo
        balance_frame = tk.Frame(top_frame)
        balance_frame.pack(side='left', padx=5)
        self.tipo_operacao = tk.Frame(top_frame)
        self.tipo_operacao.pack(side='right', padx=2)
        self.trade_mode = tk.StringVar(value="SIMULADO")
        # Adicionar o drop-down para selecionar o modo de trading
        self.create_trade_mode_dropdown()

        contadores_frame = tk.Frame(cont_frame)
        global balance_label, balance_value
        self.balance_label = tk.Label(balance_frame, text="Saldo da Conta: ")
        self.balance_label.pack()
        self.balance_value = tk.Label(balance_frame, text="")
        self.balance_value.pack(side='left', padx=5)
        global resultado_label, resultado_acumulado
        self.resultado_label = tk.Label(balance_frame, text="Resultado acumulado: ")
        self.resultado_label.pack()
        self.resultado_acumulado = tk.Label(balance_frame, text="")
        self.resultado_acumulado.pack(side='right', padx=5)

        # ====================== colocar data de início =========== 
        # Criar os rótulos de data e hora
        self.hora_inicio_label = tk.Label(balance_frame, text="")
        self.hora_inicio_label.pack(side='right', padx=5)
        self.hora_atual_label = tk.Label(balance_frame, text="")
        self.hora_atual_label.pack(side='right', padx=5)

        # Obter a hora de início e exibir
        hora_inicio = time.strftime("%d/%m/%Y %H:%M:%S")
        self.hora_inicio_label.config(text=f"Início: {hora_inicio}")
        global max_trades_var
        # Caixa para o número máximo de trades
        max_trades_frame = tk.Frame(top_frame)
        max_trades_frame.pack(side='left', padx=5)
        """     self.max_trades_label = tk.Label(max_trades_frame, text="Número Máximo de Trades:")
        self.max_trades_label.pack()
        max_trades_var = tk.StringVar(value=str(max_trades))
        self.max_trades_value = tk.Label(max_trades_frame, textvariable=max_trades_var)
        self.max_trades_value.pack() """
        # Substitua o Label por um Entry
        self.max_trades_label = tk.Label(max_trades_frame, text="Número Máximo de Trades:")
        self.max_trades_label.pack()

        # Criar uma variável StringVar para armazenar o valor do Entry
        max_trades_var = tk.StringVar(value=str(max_trades))

        # Substituir o Label pelo Entry
        self.max_trades_value = tk.Entry(max_trades_frame, textvariable=max_trades_var, justify="center")
        self.max_trades_value.pack()

        # Para obter o valor atual do Entry:
        # max_trades = self.max_trades_value.get()


        # Caixa para a entrada de texto do tamanho do trade
        trade_size_frame = tk.Frame(top_frame)
        trade_size_frame.pack(side='left', padx=5)     
        #=================== novo tradesize definido pelo chatgpt
        # Label descritivo
        
        self.trade_size_label = tk.Label(trade_size_frame, text="Tamanho do Trade:")
        self.trade_size_label.pack()

        # Entry para a entrada de texto do tamanho do trade
        self.trade_size_entry = tk.Entry(trade_size_frame,width=6, justify='center')
        self.trade_size_entry.pack()
        self.trade_size_entry.insert(0, "100.0")  # Exemplo de valor inicial
        # LAbel para especificar a alavancagem -- com default
        
        leverage_frame = tk.Frame(top_frame)
        leverage_frame.pack(side='left', padx=5)   
        # Label descritivo
        self.leverage_label = tk.Label(leverage_frame, text="Alavancagem:")
        self.leverage_label.pack()
        # Entry para a entrada de texto do tamanho do trade
        self.leverage_entry = tk.Entry(leverage_frame,width=3, justify='center')
        self.leverage_entry.pack()
        self.leverage_entry.insert(0, "20")  # Exemplo de valor inicial
        # Especificar o timeframe com 15m como default===============
        tframe_frame = tk.Frame(top_frame)
        tframe_frame.pack(side='left', padx=5)   
        # Label descritivo
        self.tframe_label = tk.Label(tframe_frame, text="Time Frame:")
        self.tframe_label.pack()
        # Entry para a entrada de texto do tamanho do trade
        self.tframe_entry = tk.Entry(tframe_frame,width=3, justify='center')
        self.tframe_entry.pack()
        self.tframe_entry.insert(0, "15")  # Exemplo de valor inicial
        # Frame de contadores ===================
        contadores_frame = tk.Frame(cont_frame)
        contadores_frame.pack(side='left', padx=5)

        prof_loss_frame = tk.Frame(cont_frame)
        prof_loss_frame.pack(side='left', padx=5)

        # ========= botão para ativar/inativar a abertura de trades == inicial = ativo
        # Criando um frame para os labels de lucro e prejuízo
        labels_frame = tk.Frame(prof_loss_frame)
        labels_frame.pack(fill="both", expand=True)  # Ocupa todo o espaço do prof_loss_frame
        # Labels dentro do labels_frame
        self.trade_c_lucro_label = tk.Label(labels_frame, text="0.00")
        self.trade_c_lucro_label.pack(side='top', padx=5)
        self.trade_c_prej_label = tk.Label(labels_frame, text="0.00")
        self.trade_c_prej_label.pack(side='top', padx=5)

        # Criar a StringVar e o botão
        global ativo
        self.ativo_var = tk.StringVar(value="ativo")
        self.botao_ativo = tk.Button(cont_frame, textvariable=self.ativo_var, command=self.toggle_ativo, bg="green", text="Ativo", width=7, height=2)
        self.botao_ativo.pack(side="right")
        #self.botao_ativo = tk.Button(cont_frame, textvariable=ativo, command=self.toggle_ativo, bg="green", text="Ativo", width=7, height=2)
        #self.botao_ativo.pack(side="right")
        # ==================

        # Labels para os contadores =======================
        self.abertos_label = tk.Label(contadores_frame, text="Total abertos:")
        self.abertos_label.pack(side='left', padx=5)
        self.abertos_count = tk.Label(contadores_frame, text="0")
        self.abertos_count.pack(side='left', padx=20)

        self.log_trades_label = tk.Label(contadores_frame, text="Long trades:")
        self.log_trades_label.pack(side='left', padx=5)
        self.log_trades_count = tk.Label(contadores_frame, text="0")
        self.log_trades_count.pack(side='left', padx=20)

        self.short_trades_label = tk.Label(contadores_frame, text="Short trades:")
        self.short_trades_label.pack(side='left', padx=5)
        self.short_trades_count = tk.Label(contadores_frame, text="0")
        self.short_trades_count.pack(side='left', padx=20)

        self.closed_trades_label = tk.Label(contadores_frame, text="Closed trades:")
        self.closed_trades_label.pack(side='left', padx=5)
        self.closed_trades_count = tk.Label(contadores_frame, text="0")
        self.closed_trades_count.pack(side='left', padx=20)

        # Log de Trades
        global log_box
        self.log_box = tk.Text(self, height=10, width=250)
        self.log_box.pack(padx=10, pady=10)
        self.log_box.tag_config("info", foreground="orange", font=("Helvetica", 10, "bold"))
        self.log_box.tag_config("important", foreground="red", font=("Helvetica", 10, "bold"))
        self.log_box.tag_config("infoblue", foreground="blue", font=("Helvetica", 10, "bold"))
        self.log_box.insert(tk.END, "Log de Trades:\n")

        # Frame para informações dos trades abertos com rolagem
        self.open_trades_frame = tk.Frame(self)
        self.open_trades_frame.pack(fill='both', expand=True, pady=10, padx=10)

        self.open_trades_label = tk.Label(self.open_trades_frame, text="Trades Abertos")
        self.open_trades_label.pack(anchor='w')

        # Canvas com frame interno e scrollbar para rolagem
        canvas = tk.Canvas(self.open_trades_frame)
        scroll_y = tk.Scrollbar(self.open_trades_frame, orient="vertical", command=canvas.yview)
        self.trades_container = tk.Frame(canvas)

        # Configurar o canvas para rolagem
        self.trades_container.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.trades_container, anchor="nw")
        canvas.configure(yscrollcommand=scroll_y.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        start_button = tk.Button(self, text="Iniciar Bot", command=self.on_start_bot)
        start_button.pack()
        # Verificar o botão de parada e gerar função stop_bot
        #stop_button = tk.Button(self, text="Parar Bot", command=stop_bot)
        #stop_button.pack()
        # criação do drop-down
    def create_trade_mode_dropdown(self):
        # Label para o modo de trading
        mode_label = tk.Label(self.tipo_operacao, text="Modo de Trading:")
        mode_label.pack()

        # Drop-down para selecionar o modo de trading
        mode_dropdown = tk.OptionMenu(self.tipo_operacao, self.trade_mode, "SIMULADO", "REAL", command=self.change_trade_mode)
        mode_dropdown.pack()

    def on_start_bot(self):
        #loop = asyncio.get_event_loop()
        #loop.create_task(start_bot())
        start_bot()
    def change_trade_mode(self, mode):
        global tcl
        # Atualizar a cor de fundo do frame principal com base no modo de trading
        if mode == "SIMULADO":
            self.tipo_operacao.config(bg='red')
            tcl = trade4fake()
            balance = 1000
        else:
            self.tipo_operacao.config(bg='lightgreen')
            tcl = trade4real()
            update_balance_inicial()



    def open_new_trade_box(self, direction, symbol, entry_price, stop_loss, take_profit, current_price):
        # global log_box
        # print('open_new_trade_box &&&&&&&&&&&&')
        #op_price = (take_profit - entry_price)/entry_price * 100
        # op_price = open_trades[symbol]['open_price']
        sloss = open_trades[symbol]['stop_loss']  #(entry_price-stop_loss)/entry_price*100

        gain = f"{take_profit}\n{entry_price}"
        loss = f"{stop_loss}\n{sloss}"
        trade_box = TradeBox(self.trades_container, open_trades[symbol]['direction'].upper(), symbol, open_trades[symbol]['open_price'], open_trades[symbol]['stop_loss'], open_trades[symbol]['stop_gain'], current_price, open_trades[symbol])
        if symbol not in app.trade_boxes.keys():
            self.trade_boxes[symbol] = trade_box
        else:
            print(f'>>>>>>>>> definição duplicada na trade boxes : {symbol}')
        trade_box.pack(padx=0, pady=0, fill=tk.X)
        self.log_box.insert(tk.END, f"Novo Trade Aberto: {symbol}\n")
        # self.log_trade(f'')

    def close_trade_box(self, symbol):
        global closed_trades_count
        if symbol in self.trade_boxes:
            trade_box = self.trade_boxes[symbol]
            trade_box.destroy()
            del self.trade_boxes[symbol]
            closed_trades_count += 1

    def update_balance(self,symbol, direction, valor):
        
        global balance, trade_size

        balance +=  valor
        self.update_balance_display()
        # self.update()




    def update_counters(self, symbol, total_trades_count, long_trades_count,short_trades_count, closed_trades_count ):
        # global long_trades_count, short_trades_count, closed_trades_count, log_box
        self.trade_counters = f"Longs Abertos: {long_trades_count}, Shorts Abertos: {short_trades_count}, Trades Fechados: {closed_trades_count}\n"
        print(f'{self.trade_counters} Entrou no update counters &&&*****&&&& =================================================================================================')
        self.abertos_count.config(text=str(total_trades_count))
        self.log_trades_count.config(text=str(long_trades_count))
        self.short_trades_count.config(text=str(short_trades_count))
        self.closed_trades_count.config(text=str(closed_trades_count))
        self.log_box.insert(tk.END, self.trade_counters + "   ")

    def log_message(self, message, style = 'normal'):
        self.log_box.insert(tk.END, message + "\n", style)
        self.log_box.see(tk.END)
    
    def log_trade(self,trade_info):    
        try:
            self.log_box.insert(tk.END, trade_info + "\n")
            with open(f"trades_log.csv", "a") as log_file:
                log_file.write(trade_info + "\n")
        except Exception as e:
            print(f'Erro no log_trade : {e}****')
        
    #Atualiza o texto do Label balance_value com o saldo atual
    def update_balance_display(self):
        global balance
        self.balance_label.config(text=f"${balance:.2f}")

    def get_trade_size(self):
        # Aqui você pode obter o valor diretamente do campo Entry
        global trade_size, tf, lev
        try:
            # Obtém o valor do Entry e converte para float
            trade_size = float(self.trade_size_entry.get())
            tf = self.tframe_entry.get()
            return float(self.trade_size_entry.get())
        except ValueError:
            return 0.0
    
    def get_max_trades(self):
        # Aqui você pode obter o valor diretamente do campo Entry
        try:
            return int(self.max_trades_value.get())
        except ValueError:
            return 0

    def toggle_ativo(self):
        global ativo
        if self.ativo_var.get() == "ativo":
            ativo = False
            self.ativo_var.set("inativo")
            self.botao_ativo.config( bg="red")   
        else:
            ativo = True
            self.ativo_var.set("ativo")
            self.botao_ativo.config( bg="green")
        

    def update_resultado(self, resultado_acumulado):
        self.resultado_acumulado.config(text="{:.2f}".format(resultado_acumulado))

    def update_lucro_prejuizo(self, trade_c_lucro, trade_c_prej):
        self.trade_c_lucro_label.config(text="{:.2f}".format(trade_c_lucro))
        self.trade_c_prej_label.config(text="{:.2f}".format(trade_c_prej))

    def update_hora_atual(self):

        # Atualizar a hora atual
        hora_atual = time.strftime("%d/%m/%Y %H:%M:%S")
        self.hora_atual_label.config(text=f"Agora: {hora_atual}")
        # Agendar a próxima atualização em 1 segundo (1000 milissegundos)
        self.after(1000, self.update_hora_atual)

    def update_trade_box_labels(self, trade, current_price, stoploss, TProfit):
        global open_trades
        # price_change = calculate_percentage_change(open_trades[symbol]['open_price'], current_price)
        symbol = trade
        precisao = open_trades[symbol]['precisao']

        try:
            trade_box = self.trade_boxes[symbol]
        except Exception as er:
            print(f"trade aberto e fechado")
            print(f"Erro no update_trade_bo_labels {symbol} : {er}")
        
        profit= calculate_percentage_change(open_trades[symbol]['open_price'], current_price, open_trades[symbol]['direction'])
        profit_entry = abs(open_trades[symbol]['stop_gain'] - open_trades[symbol]["open_price"])/open_trades[symbol]['open_price'] * 100
        color = 'green'
        if (open_trades[symbol]['direction'] == 'long' and open_trades[symbol]['open_price'] > current_price) or\
              (open_trades[symbol]['direction'] == 'short' and\
                open_trades[symbol]['open_price'] < current_price):
            color='red'
    
        #profit_entry = calculate_percentage_change(open_trades[symbol]['open_price'],open_trades[symbol]['stop_gain'],open_trades[symbol]['direction'])
        trade_box.current_price_label.config(text=f"Último preço: {current_price:.{open_trades[symbol]['precisao']}f}", fg=color)
        
        pnl = (profit * lev * trade_size) / 100
        if open_trades[symbol]['direction'] == 'long':

            cor = "blue" if stoploss >= open_trades[symbol]['open_price'] else "red"
        else:
            cor = "blue" if stoploss <= open_trades[symbol]['open_price'] else "red"

        trade_box.stop_loss_label.config(text=f"Stop_loss: {stoploss:.{open_trades[symbol]['precisao']}f}", fg=cor)
        trade_box.take_profit_label.config(text=f"Take_profit: {TProfit:.{open_trades[symbol]['precisao']}f}\n{profit_entry:.2f}%", fg="blue")
        
        trade_box.profit_label.config(text=f'Profit:  {profit:.2f}%', fg=color, font=8)
        trade_box.pnl_label.config(text=f'pnl: {pnl:.2f}', fg=color,font=8)
        trade_box.update()
# Atualizar a hora a cada segundo
# app.update_hora_atual()


def condicao_long_normal(dfcl, current_price):

    
    difmin = abs(current_price- dfcl['5min'].iloc[-1]) < abs(current_price- dfcl['5max'].iloc[-1])
    cruza_stoch1 = dfcl['cross_stoch'].iloc[-1] > 0 and dfcl['ema42'].iloc[-1] <= current_price and dfcl['cross_counter'].iloc[-1] >= 0
    cruza_stoch2 = dfcl['%K'].iloc[-1] - dfcl['%K'].iloc[-2] > 0 and dfcl['momentum'].iloc[-1] - dfcl['momentum'].iloc[-2 ] > 0  and dfcl['psar'].iloc[-1] < current_price # psar esta indicando short e pode estar esgotando
    
    if (cruza_stoch1 and cruza_stoch2) and  dfcl['%K'].iloc[-1] < 65 :
        print ('Pelo menos um .... ')
    cruza_stoch = cruza_stoch1 and cruza_stoch2
    print (f" 5min {dfcl['5min'].iloc[-1]}  Open : {dfcl['open'].iloc[-1]}")
    
    if cruza_stoch:
        print(f"psar couter = {dfcl['psar_counter'].iloc[-1]}")
        return True
    else:
        return False
def condicao_long_lw9_1(dfcl, current_price):
    cruza = dfcl['ema12'].iloc[-3] > dfcl['ema12'].iloc[-2] < dfcl['ema12'].iloc[-1] and dfcl['ema42'].iloc[-1] < current_price
    if cruza :
        return True
    else:
        return False
def condicao_short_lw9_1(dfcl, current_price):
    cruza = dfcl['ema12'].iloc[-3] < dfcl['ema12'].iloc[-2] > dfcl['ema12'].iloc[-1] and dfcl['ema42'].iloc[-1] > current_price
    if cruza :
        return True
    else:
        return False
    #current_price > dfcl['ema42'].iloc[-1] and    # current_price < dfcl['ema42'].iloc[-1] and
"""class richarddennis():


    def __init__(self):
        self.periodo_ema12 = 9 #parametros['periodo_atr']
        self.multiplicador_atr = 2 #parametros['multiplicador_atr']   

    def condicao_long(self, dfcl,current_price):    
        verde = dfcl['open'].iloc[-1] < dfcl['close'].iloc[-1]
        vermelho = dfcl['open'].iloc[-1] >  dfcl['close'].iloc[-1]
   
        cond1 = dfcl['open'].iloc[-1] >= dfcl['minimo_20_periodos'].iloc[-1] and verde
        if cond1 : #and current_price > dfcl['SUPERtrend'].iloc[-1]:
            #calculo do stop_loss

           # print(f"current_price : {current_price} maxima_20 : { dfcl['maximo_20_periodos'].iloc[-1]} ")
            return True
        else:
            return False 
    def saida_long(self,dfcl, current_price):
        verde = dfcl['open'].iloc[-1] < dfcl['close'].iloc[-1]
        vermelho = dfcl['open'].iloc[-1] >  dfcl['close'].iloc[-1]
        cond1 = current_price <= dfcl['minimo_10_periodos'].iloc[-1]
        cond2 = dfcl['open'].iloc[-1] > dfcl['maximo_10_periodos'].iloc[-1] and vermelho
        if cond2:
            return True
        else:
            return False
    def condicao_short(self, dfcl,current_price):
        verde = dfcl['open'].iloc[-1] < dfcl['close'].iloc[-1]
        vermelho = dfcl['open'].iloc[-1] >  dfcl['close'].iloc[-1]
        cond1 = dfcl['open'].iloc[-1] <= dfcl['maximo_20_periodos'].iloc[-1] and vermelho
        if cond1 :
            
            return True
        else:
            return False
    def saida_short(self, dfcl,current_price):
        verde = dfcl['open'].iloc[-1] < dfcl['close'].iloc[-1]
        vermelho = dfcl['open'].iloc[-1] >  dfcl['close'].iloc[-1]
        cond1 = dfcl['open'].iloc[-1] >= dfcl['minimo_10_periodos'].iloc[-1] and verde
     
        if cond1:
            return True
        else:
            return False"""

class estratgia_super_trend():
     def __init__(self):
        self.periodo_ema12 = 9 #parametros['periodo_atr']
        self.multiplicador_atr = 2 #parametros['multiplicador_atr']  
    # testa entrada para long
     def condicao_long(self, dfcl,current_price):    
         cond1 = dfcl['SUPERtrend'].iloc[-1] < dfcl['open'].iloc[-1] and \
         dfcl['SUPERtrend'].iloc[-2] > dfcl['close'].iloc[-2]
         if cond1:
             return True
         else:
             return False
     def condicao_short(self, dfcl, current_price):
         cond1 = dfcl['SUPERtrend'].iloc[-1] > dfcl['close'].iloc[-1] and \
         dfcl['SUPERtrend'].iloc[-2] < dfcl['open'].iloc[-2]
         if cond1:
             return True
         else:
             return False
     def saida_long(self, dfcl, current_price):
        cond1 = dfcl['SUPERtrend'].iloc[-1] > dfcl['close'].iloc[-1] and \
         dfcl['SUPERtrend'].iloc[-2] < dfcl['open'].iloc[-2]
        if cond1:
             return True
        else:
             return False
     def saida_short(self, dfcl, current_price):
        cond1 = dfcl['SUPERtrend'].iloc[-1] < dfcl['open'].iloc[-1] and \
         dfcl['SUPERtrend'].iloc[-2] > dfcl['close'].iloc[-2]
        if cond1:
             return True
        else:
             return False
class estrategia_mix():
     global quem_entra 
     def __init__(self):
        self.periodo_ema12 = 9 #parametros['periodo_atr']
        self.multiplicador_atr = 2 #parametros['multiplicador_atr']

     def condicao_long(self, dfcl,current_price, symbol):
        
        cruza = dfcl['ema12'].iloc[-1] > dfcl['ema28'].iloc[-1] and dfcl['open'].iloc[-1] <= dfcl['ema12'].iloc[-1] and\
        dfcl['close'].iloc[-1] >= dfcl['ema12'].iloc[-1]
           # (dfcl['ema12'].iloc[-2] < dfcl['ema28'].iloc[-2] or dfcl['ema12'].iloc[-3] < dfcl['ema28'].iloc[-3])#and dfcl['momentum'].iloc[-1] > dfcl['momentum'].iloc[-2]#  dfcl['ema12'].iloc[-1] / dfcl['ema12'].iloc[-2] > 1.003 and
        cruza2 = (dfcl['%K'].iloc[-1] > dfcl['%D'].iloc[-1] and dfcl['%K'].iloc[-2] <= dfcl['%D'].iloc[-2] and 
                  dfcl['momentum'].iloc[-1] >  dfcl['momentum'].iloc[-2]  and dfcl['%K'].iloc[-1] < 35)
        cruza3 = dfcl['ema12'].iloc[-5] > dfcl['ema12'].iloc[-4] > dfcl['ema12'].iloc[-3] > dfcl['ema12'].iloc[-2] <\
              dfcl['ema12'].iloc[-1] and dfcl['close'].iloc[-1] > dfcl['ema12'].iloc[-1] and dfcl['ema12'].iloc[-1] >\
              dfcl['ema12'].iloc[-2] and  current_price > dfcl['ema42'].iloc[-1]

        cruza4 = dfcl['SUPERtrend'].iloc[-2] >= dfcl['close'].iloc[-2]  and \
            dfcl['SUPERtrend'].iloc[-1] < dfcl['close'].iloc[-1] 
        cruza5 = dfcl['5min'].iloc[-3] > dfcl['5min'].iloc[-2] < dfcl['5min'].iloc[-1] and\
              (dfcl['open'].iloc[-1] < dfcl['5min'].iloc[-1] and dfcl['close'].iloc[-1] >= dfcl['5min'].iloc[-1] ) 
        cruza6 = dfcl['open'].iloc[-1] < dfcl['close'].iloc[-1] and\
                  current_price >= dfcl['open'].iloc[-1]
        cruza7 = dfcl["MACD"].iloc[-1] >= dfcl['signal'].iloc[-1] and dfcl["MACD"].iloc[-2] <= dfcl['signal'].iloc[-2] # and\
                # dfcl['SUPERtrend'].iloc[-1] <= current_price
                #dfcl['ema12'].iloc[-2] < dfcl['ema12'].iloc[-1] and dfcl['ema12'].iloc[-1] < dfcl['ema28'].iloc[-1]

        if cruza7 : # and  dfcl['SUPERtrend'].iloc[-1] < dfcl['close'].iloc[-1] : #or cruza4 or cruza3 or (cruza5 and cruza6) or (cruza5 and cruza7) : # adicionado o supertrend or cruza5

                
            if cruza7:
                print(f"{Fore.RED}%K -1 : {Fore.WHITE}{ dfcl['%K'].iloc[-1] } {Fore.RED} %D -1 : {Fore.WHITE}{dfcl['%D'].iloc[-1]}{Style.RESET_ALL}")
                app.log_message ("Entrou pelo cruza7 (MACD) long " ,"info")
                quem_entra = "cruza - long"

            return True
        else:
            return False
     def condicao_short(self, dfcl, current_price, symbol):
        cruza = dfcl['ema12'].iloc[-1] < dfcl['ema28'].iloc[-1] and dfcl['open'].iloc[-1] >= dfcl['ema12'].iloc[-1] and\
        dfcl['close'].iloc[-1] <= dfcl['ema12'].iloc[-1]
        cruza2 = dfcl['%K'].iloc[-1] < dfcl['%D'].iloc[-1] and dfcl['%K'].iloc[-2] >= dfcl['%D'].iloc[-2] and dfcl['momentum'].iloc[-1] < dfcl['momentum'].iloc[-2] and dfcl['%K'].iloc[-1] > 65
        
        cruza3 = dfcl['ema12'].iloc[-5] < dfcl['ema12'].iloc[-4] < dfcl['ema12'].iloc[-3] < dfcl['ema12'].iloc[-2] > dfcl['ema12'].iloc[-1] and dfcl['close'].iloc[-1] < dfcl['ema12'].iloc[-1] and dfcl['ema12'].iloc[-1] < dfcl['ema12'].iloc[-2]  and current_price < dfcl['ema28'].iloc[-1]
        cruza4 = dfcl['SUPERtrend'].iloc[-2] <= dfcl['open'].iloc[-2]  and dfcl['SUPERtrend'].iloc[-1] > dfcl['close'].iloc[-1] 
        cruza5 = dfcl['5max'].iloc[-3] < dfcl['5max'].iloc[-2] > dfcl['5max'].iloc[-1] and\
              (dfcl['open'].iloc[-1] >= dfcl['5max'].iloc[-1] and dfcl['close'].iloc[-1] < dfcl['5max'].iloc[-1] ) 
        cruza6 = dfcl['open'].iloc[-1] > dfcl['close'].iloc[-1]and current_price <= dfcl['open'].iloc[-1]
        cruza7 = dfcl["MACD"].iloc[-1] <= dfcl['signal'].iloc[-1] and dfcl["MACD"].iloc[-2] >= dfcl['signal'].iloc[-2]  # and\
                # dfcl['SUPERtrend'].iloc[-1] >= current_price
                # dfcl['ema12'].iloc[-2] > dfcl['ema12'].iloc[-1] and dfcl['ema12'].iloc[-1] > dfcl['ema28'].iloc[-1]
        if cruza7 :# and dfcl['SUPERtrend'].iloc[-1] > dfcl['close'].iloc[-1] :# (cruza3  or cruza4 or cruza or  (cruza5 and cruza6))  :  # colquei verificação da posição do estocástico ...or cruza2 or cruza5
            if cruza7 :
                print(f"Entrou pelo cruza7 MACD short ")
                app.log_message("Entrou pelo cruza7 short - MACD" ,"info")
                quem_entra = "cruza5 - short"

            return True
        else:
            return False
     def saida_long(self, dfcl, current_price, symbol):
        cruza = dfcl['ema12'].iloc[-1] < dfcl['ema28'].iloc[-1] and (dfcl['ema12'].iloc[-2] >= dfcl['ema28'].iloc[-2] or\
                                                                     dfcl['ema12'].iloc[-3] >= dfcl['ema28'].iloc[-3])
        cruza1 = dfcl['close'].iloc[-1] < dfcl['ema12'].iloc[-1]
        cruza5 = dfcl['5min'].iloc[-3] < dfcl['5min'].iloc[-2] > dfcl['5min'].iloc[-1] and\
              dfcl['open'].iloc[-1] > dfcl['5min'].iloc[-1] and dfcl['close'].iloc[-1] < dfcl['5min'].iloc[-1] 
        cruza7 = dfcl["MACD"].iloc[-1] <= dfcl['signal'].iloc[-1] and dfcl["MACD"].iloc[-2] >= dfcl['signal'].iloc[-2]  and\
                dfcl['SUPERtrend'].iloc[-1] >= current_price
        sl_on = current_price <= open_trades[symbol]['stop_loss']
        # teste. Media de preço do candle atual abaixo da ema12 como sinal se saída do long
       
        if  cruza7  or sl_on: #or onde_mp: #cruza2 or cruza4 or cruza or (cruza5 and cruza6) or (cruza5 and cruza7):   #or   dfcl['SUPERtrend'].iloc[-1] >  dfcl['open'].iloc[-1] or cruza5
            if sl_on:
                app.log_message(f" Saiu pelo stop_loss {current_price}","info")
            if cruza7 :
                app.log_message("saiu pelo MACD \n" ,"info")
                quem_entra = "cruza - long"

            return True
        else:
            return False
        
     def saida_short(self, dfcl, current_price, symbol):
        cruza = dfcl['ema12'].iloc[-1] > dfcl['ema28'].iloc[-1] and dfcl['ema12'].iloc[-2] <= dfcl['ema28'].iloc[-2] 
        cruza1 = dfcl['close'].iloc[-1] > dfcl['ema12'].iloc[-1]
        cruza5 = dfcl['5max'].iloc[-3] < dfcl['5max'].iloc[-2] >= dfcl['5max'].iloc[-1] and\
              dfcl['open'].iloc[-1] > dfcl['5max'].iloc[-1] and dfcl['close'].iloc[-1] < dfcl['5max'].iloc[-1] 
        cruza7 = dfcl["MACD"].iloc[-1] >= dfcl['signal'].iloc[-1] and dfcl["MACD"].iloc[-2] <= dfcl['signal'].iloc[-2] and\
                dfcl['SUPERtrend'].iloc[-1] <= current_price
        sl_on = current_price >= open_trades[symbol]['stop_loss']
         # teste. Media de preço do candle atual abaixo da ema12 como sinal se saída do long
       
        if  cruza7 : #or onde_mp: # cruza2 or cruza3 or cruza4 or  (cruza5 and cruza6) or (cruza5 and cruza7): #or  dfcl['SUPERtrend'].iloc[-1] <  dfcl['open'].iloc[-1]  or cruza5
            print(f"Saiu pelo MACD (emacross)")
            app.log_message('saiu pelo cruza (emacross)', 'info')
            if sl_on:
                print(f"Saiu pelo stop_loss {open_trades[symbol]['stop_loss']} ")
                app.log_message(f"Saiu pelo stop_loss {open_trades[symbol]['stop_loss']} ", 'info')
            return True
        else:
            return False
# inicio classe estrategia_lw9_4 ================================
class estrategia_cross_ema12():
    def __init__(self):
        self.periodo_ema12 = 9 #parametros['periodo_atr']
        self.multiplicador_atr = 2 #parametros['multiplicador_atr']

    def condicao_long(self,dfcl,current_price):
        print(f'Entrou no teste para long')
        cruza = dfcl['ema12'].iloc[-1] > dfcl['ema28'].iloc[-1] and dfcl['ema12'].iloc[-2] < dfcl['ema28'].iloc[-2] 
        cruza2 = dfcl['%K'].iloc[-1] > dfcl['%D'].iloc[-1] and dfcl['%K'].iloc[-2] <= dfcl['%D'].iloc[-2] and dfcl['momentum'].iloc[-1] >  dfcl['momentum'].iloc[-2] # and dfcl['ema12'].iloc[-1] > dfcl['ema12'].iloc[-2]
        #print(f'{Fore.BLUE}Entrou no teste para long cruza = {cruza}{Style.RESET_ALL}')
        if cruza or cruza2:
            return True
        else:
            return False
        

    def condicao_short(self, dfcl, current_price):
        cruza = dfcl['ema12'].iloc[-1] < dfcl['ema28'].iloc[-1] and dfcl['ema12'].iloc[-2] > dfcl['ema28'].iloc[-2]  # and dfcl['momentum'].iloc[-1] < dfcl['momentum'].iloc[-2]
        # print(f'{Fore.BLUE}Entrou no teste para short cruza = {cruza}{Style.RESET_ALL}')
        if cruza:
            return True
        else:
            return False
        
    def saida_long(self, dfcl, current_price):
        cruza1 = dfcl['ema12'].iloc[-1] < dfcl['ema28'].iloc[-1] and dfcl['ema12'].iloc[-2] >= dfcl['ema28'].iloc[-2] 
        # cruza2 = dfcl['ema12'].iloc[-1] <= dfcl['ema12'].iloc[-2] ## dfcl['ema12'].iloc[-5] <  saiu do inicio da expressão abaixo
        cruza2 = dfcl['ema12'].iloc[-4] < dfcl['ema12'].iloc[-3] < dfcl['ema12'].iloc[-2] > dfcl['ema12'].iloc[-1] and dfcl['close'].iloc[-1] < dfcl['ema28'].iloc[-1] # and dfcl['ema12'].iloc[-1] < dfcl['ema12'].iloc[-2]
        cruza3 = padrao_candle(dfcl,"long")
        if cruza1: # or cruza3:
            return True
        else:
            return False
        
    def saida_short(self, dfcl, current_price):
        cruza1 = dfcl['ema12'].iloc[-1] > dfcl['ema28'].iloc[-1] and dfcl['ema12'].iloc[-2] <= dfcl['ema28'].iloc[-2] 
        #cruza2 = dfcl['ema12'].iloc[-1] >= dfcl['ema12'].iloc[-2] # dfcl['ema12'].iloc[-5] >  Saiu da expressão abaixo
        cruza2 = dfcl['ema12'].iloc[-4] > dfcl['ema12'].iloc[-3] > dfcl['ema12'].iloc[-2] < dfcl['ema12'].iloc[-1] and dfcl['close'].iloc[-1] > dfcl['ema28'].iloc[-1] # and dfcl['ema12'].iloc[-1] > dfcl['ema12'].iloc[-2] 
        cruza3 = padrao_candle(dfcl,"short")
        if cruza1 :  #or  cruza3:
            return True
        else:
            return False


class estrategia_lw9_4 ():
    def __init__(self):
        # Armazena os parâmetros da estratégia
        self.periodo_atr = 14 #parametros['periodo_atr']
        self.multiplicador_atr = 2 #parametros['multiplicador_atr']
        # ... outros parâmetros 
    def condicao_long (self, dfcl, current_price):
        cruza = dfcl['ema12'].iloc[-5] > dfcl['ema12'].iloc[-4] > dfcl['ema12'].iloc[-3] > dfcl['ema12'].iloc[-2] < dfcl['ema12'].iloc[-1] and dfcl['close'].iloc[-1] > dfcl['ema12'].iloc[-1] and dfcl['ema12'].iloc[-1] > dfcl['ema12'].iloc[-2] 
        if cruza:
            return True
        else:
            return False
    def saida_long(self, dfcl, current_price):
        if dfcl['close'].iloc[-1] < dfcl['ema12'].iloc[-1]:
            return True
        else:
            return False
    def condicao_short(self, dfcl, current_price):
        cruza = dfcl['ema12'].iloc[-5] < dfcl['ema12'].iloc[-4] < dfcl['ema12'].iloc[-3] < dfcl['ema12'].iloc[-2] > dfcl['ema12'].iloc[-1] and dfcl['close'].iloc[-1] < dfcl['ema12'].iloc[-1] and dfcl['ema12'].iloc[-1] < dfcl['ema12'].iloc[-2] 
        if cruza : 
            return True
        else:
            return False
    def saida_short(self, dfcl, current_price):
        if dfcl['close'].iloc[-1] > dfcl['ema12'].iloc[-1]:
            return True
        else:
            return False
# Fim da classe estrategia_lw9_4 =================================================================
def condicao_long_atr(dfcl,current_price):
    cruza = dfcl['atr'].iloc[-2] >= current_price and dfcl['atr'].iloc[-1] <= current_price
    if cruza:
        return True
    else:
        return False
def condicao_long(dfcl, current_price):
    cruza1 = dfcl["cross_counter"].iloc[-1] in range(1,10) and  dfcl['ema12'].iloc[-1] - dfcl['ema12'].iloc[-2] > 0
    cruza2 = dfcl['psar'].iloc[-1] > current_price and dfcl["%K"].iloc[-1] - dfcl["%K"].iloc[-2]  >= 0
    if cruza1 and cruza2 :
        return True
    else:
        return False
def condicao_short(dfcl, current_price):
        cruza1 = dfcl["cross_counter"].iloc[-1] in range(-10,0) and   dfcl['ema12'].iloc[-1] - dfcl['ema12'].iloc[-2] < 0
        cruza2 = dfcl['psar'].iloc[-1] < current_price and dfcl["%K"].iloc[-1] - dfcl["%K"].iloc[-2] <= 0
        if cruza1 and cruza2 :
            return True
        else:
            return False
def condicao_short_normal(dfcl, current_price):
    try:
            difmax = abs(current_price- dfcl['5min'].iloc[-1]) > abs(current_price- dfcl['5max'].iloc[-1])
            
            cruza_stoch1 = dfcl['cross_stoch'].iloc[-1] < 0  and dfcl['mom_counter'].iloc[-1] <= 0 and dfcl['ema42'].iloc[-1] >= current_price and dfcl['cross_counter'].iloc[-1] <= 0 # and difmax #and  dfcl['%k'].iloc[-1] > 55
            cruza_stoch2 = dfcl['%K'].iloc[-1] - dfcl['%K'].iloc[-2] < 0 and dfcl['momentum'].iloc[-1] - dfcl['momentum'].iloc[-2 ] < 0 and dfcl['psar'].iloc[-1] > current_price  #psar esta indicando long e pode estar esgotando
            #if dfcl['open'].iloc[-1] >= dfcl['5max'].iloc[-1] and dfcl['open'].iloc[-1] > dfcl['close'].iloc[-1] and dfcl['macd'].iloc[-1] < dfcl['macds'].iloc[-1]:
            cruza_stoch = cruza_stoch2 and cruza_stoch1
            if cruza_stoch  :
                print(f"psar couter = {dfcl['psar_counter'].iloc[-1]}")
                return True
            else:
                return False
    except Exception as errshort:
        print(f"errshort : {errshort}")
        tb = traceback.extract_tb(errshort.__traceback__)
        filename, line_number, function_name, text = tb[-1]
        print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {errshort}")

# Calculo do saldo ao fim de um trade
def calcular_saldo(tamanho_trade, preco_entrada, preco_saida, alavancagem, direcao):

    global balance
    # Calcular o resultado do trade com base na direção
    resultado_trade = trade_size *  (alavancagem * calculate_percentage_change(preco_entrada, preco_saida, direcao)/100)
    resul_final_trade = trade_size + resultado_trade
    if direcao=='long':
        if preco_saida < preco_entrada:
            resul_final_trade = trade_size - resultado_trade
    elif direcao =='short':
        if preco_saida > preco_entrada:
            resul_final_trade = trade_size - resultado_trade


    # Atualizar o saldo

    # balance +=  resul_final_trade
    # balance_label.config(text=f"${balance:.2f}")
    # app.balance_label.config(text=f"${balance:.2f}")


    # app.update_balance_display()
    return resul_final_trade
# pegar todos os simbolos do mercado
def calculate_percentage_change(entry_price, exit_price, direcao):

    # percentage_change = ((exit_price - entry_price) / entry_price) * 100
    if direcao =='long':
        percentage_change = abs(exit_price-entry_price)/entry_price  * 100 #Para multiplicar diretamente
    else:
        percentage_change = abs(exit_price-entry_price)/entry_price * 100

    return percentage_change
# Função para filtrar tickers e pegar apenas as chaves
def get_filtered_symbols(tickers, exclude_currencies=['USDC']):
    filtered_symbols = [symbol for symbol in tickers.keys() if not any(exclude_currency in symbol for exclude_currency in exclude_currencies)]
    filtered_symbols_rep =  [symbol.replace(':USDT', '') for symbol in filtered_symbols if ':USDT' in symbol]
    # filtered_symbols_rep = [filtered_symbols.replace(":USDT", "") for symbol in filtered_symbols if ":USDT" in symbol]
    return filtered_symbols_rep
"""def is_futures_symbol(symbol):
    global black_list
    try:
        market = exchange.fetch_market(symbol)
        return market['type'] == 'future'
    except ccxt.BaseError:
        black_list.append(symbol)
        return False"""
    
def get_all_symbols():
    global params, usdt_markets
    # markets = exchange.load_markets()   # params=params 
    # markets = exchange.load_markets()
    # markets = {symbol: market for symbol, market in markets.items() if market.get('future')}
    # symbols = [symbol for symbol in markets.keys() if symbol.endswith('/USDT')]
    # Filtrar mercados de futuros perpétuos
    # symbols = {market['id'] for market in markets if market['type'] == 'future' and market['future'] and market['expiry'] is None}
    #symbols = {}
    #usdt_markets = [market for market in markets if market['quote'] == 'USDT']
    #symbols = {symbol for symbol, market in markets.items() if market['type'] == 'future' and market['future'] and market['expiry'] is None and market['quote'] == 'USDT'}
    
    # Obter volume de 24h e rentabilidade para todos os símbolos
    tickers = exchange.fetch_tickers(params=params)
    symbols = get_filtered_symbols(tickers, exclude_currencies=['USDC'])
    # Criar dicionários de volumes e rentabilidade
    volumes = {symbol: tickers[symbol]['quoteVolume'] for symbol in symbols if symbol in tickers and 'quoteVolume' in tickers[symbol]}
    profitability = {symbol: tickers[symbol]['priceChangePercent'] for symbol in symbols if symbol in tickers and 'priceChangePercent' in tickers[symbol]}

    # Ordenar os símbolos por volume e rentabilidade em ordem decrescente
    # , -profitability.get(x, 0) 
    sorted_symbols = sorted(symbols, key=lambda x: (-profitability.get(x, 0)))
    # sorted_symbols = sorted(symbols, key=lambda x: profitability.get(x, 0), reverse=False)

    return sorted_symbols
    #return symbols
# ======= Padrão de candle como sinal de saída ========
# === deve receber um slice do df (???) verificar para long se:
# === fechamento de [-2] e abertura [-1] dentro da tolerância
# === se momentum e estochastico estão descendo (deve cumprir as duas condições) 
# === Raciocínio inverso para posição short ...
def padrao_candle(dfcl, direction):
    tolerancia_percentual = 0.0001  # Diferença fixa que você aceita
    if abs(dfcl['close'].iloc[-2] - dfcl['open'].iloc[-1]) / dfcl['open'].iloc[-1] < tolerancia_percentual and \
        dfcl['close'].iloc[-1] < dfcl['open'].iloc[-1] and direction == "long" and\
            dfcl['momentum'].iloc[-2] >  dfcl['momentum'].iloc[-1]  and  dfcl['%K'].iloc[-2] > dfcl['%K'].iloc[-1] :
        return  True
    elif abs(dfcl['close'].iloc[-2] - dfcl['open'].iloc[-1]) / dfcl['open'].iloc[-1] < tolerancia_percentual and \
        dfcl['open'].iloc[-1] < dfcl['close'].iloc[-1] and direction == "short" and\
           dfcl['momentum'].iloc[-2] >  dfcl['momentum'].iloc[-1]  and  dfcl['%K'].iloc[-2] < dfcl['%K'].iloc[-1] :
        return True
    else:
        return False
# Função para obter dados históricos
def fetch_ohlcv(symbol, timeframe=f'{tf}m', limit=100):  #mudei de 5m para 15m
    global params
    # print(f'Vai pegar os dados históricos ++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)  #, params=params)
        # if not ohlcv:
        #    log_trade(f"No data for {symbol}")
        #    return pd.DataFrame()
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['t_index'] = df['timestamp']
        # Definindo a coluna 'timestamp' como índice
        df.set_index('t_index', inplace=True)
        return df
    except Exception as e:
        black_list.append(symbol)
        # app.log_message(f"Erro ao buscar dados para {symbol}: {str(e)}")
        return pd.DataFrame()    #ERROERROERROERROERROERROERROERROERROERROER
    
# Função para obter o preço atual
def fetch_current_price(symbol):
    global params, df, timestamp_ticker
    try:
        ticker = exchange.fetch_ticker(symbol, params=params)
        if ticker['timestamp'] is not None:
            timestamp_ticker = datetime.datetime.fromtimestamp(ticker["timestamp"] / 1000)
        
    except Exception as err:
        print(f"Erro no ferch current price: {err}")
        black_list.append(symbol)
        return False
    return ticker['last'],ticker['timestamp']    
    #print(f'ticker : {ticker}')
    #print(f'ticker["timestamp"] : {ticker["timestamp"]}')
    # Converta o timestamp para uma data legível (opcional)

def validate_oco_order(self, trade_side, stop_loss, take_profit, preco_corrente, precisionP, slippage=0.005):
    
    if trade_side == 'long' or trade_side == 'buy':
        if stop_loss > preco_corrente:
            raise ValueError("Para ordens de compra, Stop Price deve ser < preço de mercado atual.")
        if take_profit < preco_corrente:
            raise ValueError("Para ordens de compra, Take Profit deve ser > preço de mercado atual.")
    elif trade_side == 'sell' or trade_side == 'short':
        if stop_loss < preco_corrente:
            raise ValueError("Para ordens de venda, Stop Price deve ser > preço de mercado atual.")
        if take_profit > preco_corrente:
            raise ValueError("Para ordens de venda, Take Profit deve ser < preço de mercado atual.")
        
def calculo_sl_tp(symbol, dfatr, open_trades=None, is_long=True):
    current_price, timestamp_ticker = fetch_current_price(symbol)

    # Calculate the size of a tick (assuming price_precision is correct)
    price_precision = exchange.markets[symbol]['precision']['price']
    tick_size = 10 ** -price_precision
    value_of_one_point = tick_size

    print(f'valor de um ponto para o symbol : {symbol} : {value_of_one_point}')

    # Define the ATR multiplier
    atr_multiplier = 2.5

    # Calculate stop-loss and take-profit in points
    stop_loss_in_points = dfatr['ATR'].iloc[-1] * atr_multiplier
    take_profit_in_points = dfatr['ATR'].iloc[-1] * atr_multiplier
    
    # Convert points to price (considering long or short position)
    if is_long:
        # stop_loss_price = dfatr['5min'].iloc[-1]  #current_price - dfatr['ATR'].iloc[-1]
        stop_loss_price = min(dfatr["low"].iloc[-5], dfatr["low"].iloc[-4],dfatr["low"].iloc[-3],dfatr["low"].iloc[-2],dfatr["low"].iloc[-1])
        #stop_loss_price = current_price + (stop_loss_in_points * value_of_one_point) * -1
        # stop_loss_price = current_price * 0.98
        take_profit_price = current_price + (take_profit_in_points * value_of_one_point)
        
    else:
        take_profit_price = current_price - (take_profit_in_points * value_of_one_point) 
        # stop_loss_price =  dfatr['5max'].iloc[-1] # current_price + (take_profit_in_points * value_of_one_point)
        stop_loss_price = max(dfatr["high"].iloc[-5], dfatr["high"].iloc[-4],dfatr["high"].iloc[-3],dfatr["high"].iloc[-2],dfatr["high"].iloc[-1])
        # stop_loss_price = current_price * 1.1
    print(f"{current_price} stop_loss: {stop_loss_price} take_profit: {take_profit_price}")
    tolerance = 1e-8
    """if abs(current_price - stop_loss_price) < tolerance:
        stop_loss_price = stop_loss_price * (1 - .012) if is_long else stop_loss_price * 1.012
        print(f"dfatr['ATR] : {dfatr['ATR'].iloc[-1]}")
        app.log_message(f"valor do ATR : {dfatr['ATR'].iloc[-1]} ","important") """
    # You can return these values or use them within your trading logic
    return current_price, stop_loss_price, take_profit_price 


class TradeBase:
    def open_trade(self, symbol, direction, price, stop_loss, take_profit):
        raise NotImplementedError

    def close_trade(self, symbol, direction):
        raise NotImplementedError
    # classe para processamento real
class trade4real(TradeBase):

    # ======= FUNÇÃO PARA CHECKAR O STATUS DE ORDEM EMITIDA ========================
    def check_order_status(self, order_id, symbol):
        try:
            order = exchange.fetch_order(order_id, symbol)
            return order['status']
        except Exception as e:
            print(f"Erro ao verificar status da ordem: {e}")
            app.log_message(f"Erro ao verificar status da ordem:","important")
            app.log_message(f"{symbol}: order_id: {order_id} :  {e}")
            return None



        # Verificação de slippage (opcional)
        stop_loss_adjusted = round(stop_loss * (1 - slippage), precisionP)
        take_profit_adjusted = round(take_profit * (1 + slippage), precisionP)
        if stop_loss_adjusted >= stop_loss:
            raise ValueError("Stop Loss ajustado é maior que o valor original.")
        if take_profit_adjusted <= take_profit:
            raise ValueError("Take Profit ajustado é menor que o valor original.")
    #=========================OPEN TRADE REAL ======================================
    def open_trade(self, symbol, direction, price, stop_loss, take_profit):
        global open_trades, max_trades, trade_size, balance, ativo, long_trades_count, short_trades_count,total_trades_count #
        
        if max_trades <= (long_trades_count + short_trades_count):
            app.log_message(f"Limite máximo de {max_trades} trades atingido.\n")
            return
        
        if trade_size >= balance:
            app.log_message(f"Saldo insuficiente {trade_size} para saldo de : {balance}.\n")
            return
        if (stop_loss == take_profit):
            trades_2_remove.append(symbol)
            black_list.append(symbol)
            return
        # Determinar os lados da ordem
        if direction == 'long':
            trade_side = "buy"
            trade_SL, trade_TP = "sell", "sell"
        elif direction == 'short':
            trade_side = "sell"
            trade_SL, trade_TP = "buy", "buy"
        else:
            print(f"Erro na direção: {direction}")
            app.log_message(f"Erro na informação de direção do trade: {direction}.\n", "important")
            return  # Adicionando o return aqui para interromper a execução se a direção estiver incorreta
        
        amount = (trade_size * lev) / price
        print(f'Amount calculado: {amount}')
        otsymbol = symbol.replace('/','')
        # Obtenha a precisão permitida para o símbolo
        try:
            
            precision = exchange.markets[symbol]['precision']['amount']
            # Calcule o número de casas decimais baseado na precisão
            decimal_places = len(str(precision).split('.')[1]) if '.' in str(precision) else 0

            # Arredonde a quantidade para a precisão correta
            amount = round(amount,decimal_places)
            #amount =  exchange.amount_to_precision(symbol, amount)
            precisionP = exchange.markets[symbol]['precision']['price']
            precisionP = len(str(precisionP).split('.')[1]) if '.' in str(precisionP) else 0

            stop_loss = float(exchange.price_to_precision(symbol,stop_loss))   #exchange.amount_to_precision(symbol, stop_loss)
            take_profit = float(exchange.price_to_precision(symbol,take_profit))  #exchange.amount_to_precision(symbol,take_profit)
        except Exception as err:
            print(f"erro no precision : {err} - saindo do trade")
            return


        
        # Configurar a margem isolada para o símbolo

        # symbol = symbol.replace('/', '')  # Certifique-se de remover a barra do símbolo para a Binance
        print(f"{Fore.RED} symbolo antes de mandar para margin: {symbol} e depois de alterado {symbol.replace('/','')}{Style.RESET_ALL}")

        try:
            response = exchange.setMarginMode ('isolated', otsymbol)   #, paramIs
            # print(f"{response} = exchange.setMarginMode ('isolated', symbol)")
            response = exchange.set_leverage(20,otsymbol)
        except Exception as e:
            print(f"{Fore.RED}Erro ao configurar margem isolada: {e}{Style.RESET_ALL}")
            return

        # Criar ordem de mercado
        preco_corrente,timestamp = fetch_current_price(symbol)
        stop_loss = float(exchange.price_to_precision(symbol,stop_loss))   #exchange.amount_to_precision(symbol, stop_loss)
        take_profit = float(exchange.price_to_precision(symbol,take_profit))  #exchange.amount_to_precision(symbol,take_profit)
        #self.validate_oco_order(direction, stop_loss, take_profit, preco_corrente,precisionP )
        # Cria a ordem de mercado
        print(f" symbol : {symbol} side: {trade_side} type : {'market'} amount: {amount } stop_loss: {stop_loss} stop_gain : {take_profit}")
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=trade_side,
            amount=amount)
        attempts = 0
        max_attempts = 5
        while attempts < max_attempts:
            try:
                order = exchange.fetch_order( order['id'], symbol.replace("/",""))
                if order['status'] == 'closed':
                    break  # Ordem fechada com sucesso
                attempts += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"Error fetching order: {e}")
                attempts += 1
  
        # Armazenar o ID da ordem
        order_id = order['id']
        open_price = order['price'] # preço executado
        amount = order['amount']   # pegando a quantidade executada para passar para as outra ordens  pendentes
        open_trades[symbol]['order_id'] = order['id']
        inverted_side = 'sell' if trade_side == 'buy' else 'buy'
        # criar uma ordem OCO para SL e TP - se uma das duas executar fecha a posição e cancela a outra
        # se a posição for fechada manualmente, basta cancelar uma delas que a outra "morre" junto - isto é um teste
        stop_limit_price = stop_loss * (1 + 0.0031) if inverted_side == 'sell' else stop_loss * ( 1 - 0.0031)
        stop_limit_price = float(exchange.price_to_precision(symbol,stop_limit_price))
        try:
           
  
                 # 'reduceOnly': True  # Garante que a ordem só reduz a posição })

        
        # insere ordem de stop_loss a limite e guarda a order_id para posterior cancelamento.

            order_sl = exchange.create_order(
            symbol=symbol,
            type='stop_market',  # Tipo de ordem para o Stop Loss
            side=inverted_side,  # 'buy' se você estiver fechando uma posição short
            amount=amount,  # Mesma quantidade da posição de entrada
            params={'stopPrice': stop_loss, 'reduceOnly' : 'true'}  # Preço de stop (trigger)
            )
            
            attempts = 0
            max_attempts = 5
            while attempts < max_attempts:
                try:
                    
                    if order_sl['status'] == 'closed' or order_sl['status'] == 'CLOSED':
                        break  # Ordem fechada com sucesso
                    attempts += 1
                    time.sleep(0.5)
                except Exception as e:
                    print(f"Error fetching order: {e}")
                    attempts += 1

        except Exception as er:
            print (f'Erro na ordem  : {er}')
        # Verificando o status da ordem"""
        order_info = exchange.fetchOrder(order_sl['id'], symbol)
        print(f'{Fore.CYAN} Indormaçoes sobre ordem gerada ================================')
        app.log_message(f"Ordem {direction} aberta para {symbol} OrderId ={open_trades[symbol]['order_id']}","infoblue")
        print(f"{order_info}{Style.RESET_ALL}")
        if order_info['status'] == 'closed':
            # Obtendo o histórico da ordem
            order_history = exchange.fetch_order(order_id, symbol)
            amount = order_history['amount']
            # open_price = order_history['price']
            print(order_history['price'], order_history['amount'])  # Preço de execução da ordem e quantidade

            order_sl_hist = exchange.fetch_order(order_sl['id'], symbol)
            SL = order_sl_hist['triggerPrice']
            open_trades[symbol]['stop_loss'] = SL


            # order_tp_hist = exchange.fetch_order(order_tp['id'], symbol)
            # take_profit = take_profit #order_tp_hist['price'] 
        open_trades[symbol] = {'open_order_id': order_id, 'symbol': symbol, 'direction' : direction, 'amount' : amount, 'open_price' : open_price, 'stop_loss': stop_loss, 'sl_order_id' : order_sl['id'] , 'stop_gain' : take_profit, 'precisao' : precisionP}  # Inicializando o dicionário de trades abertos corretamente
        
        app.log_message(f"{open_trades[symbol]['open_price']} sl : {open_trades[symbol]['stop_loss']} TP : {open_trades[symbol]['stop_gain']}","info")
        print(f"{Fore.MAGENTA}{open_trades[symbol]['open_price']} sl : {open_trades[symbol]['stop_loss']} TP : {open_trades[symbol]['stop_gain']}{Style.RESET_ALL}")
        total_trades_count += 1
        if direction == 'long':
            long_trades_count += 1
        elif direction == 'short':
            short_trades_count += 1
            
        app.update_counters(symbol,total_trades_count,long_trades_count,short_trades_count, closed_trades_count )
        update_balance_inicial()   
    # Verificação para ordens de compra
        

            #balance = get_account_balance()
            #app.balance_label.config(text=f"${balance:.2f}")
            
        app.log_message(f"Trade aberto: {symbol}, Direção: {direction}, Preço: {price}, SL: {stop_loss}, TP: {take_profit}")
        app.open_new_trade_box(direction, symbol, price, stop_loss, take_profit, price)  # Atualizado o método

        return

    #============FUNÇÃO PARA CHECK SE EXISTEM ORDENS PENDENTES E CANCELA-LAS SE POSITIVO==================================================
    # Função para verificar e cancelar ordens pendentes
    def check_and_cancel_pending_orders(symbol, order_id_to_keep):
        open_orders = exchange.fetch_open_orders(symbol)
        for order in open_orders:
            if order['id'] != order_id_to_keep and order['symbol'] == symbol:
                try:
                    exchange.cancel_order(order['id'], symbol)
                    print(f"Ordem {order['id']} cancelada.")
                except Exception as e:
                    print(f"Erro ao cancelar a ordem {order['id']}: {e}")
    # ========== FUNÇÃO PARA FECHAR TRADES ATIVOS ============
    def close_trade(self, symbol, current_price, tsclose):
        global vol_lucro, vol_preju, open_trades, closed_trades, max_trades, trade_size,\
              balance, ativo, short_trades_count, long_trades_count,\
        closed_trades_count,lev
        """
        Fecha uma posição aberta para o símbolo especificado.

        Args:
            symbol (str): O símbolo para o qual a posição deve ser fechada (por exemplo, 'BTC/USDT').
            direction (str): A direção do trade a ser fechado ('long' para posições compradas, 'short' para posições vendidas).
        """
        """ Entrei aqui pq algum evento fechou ou vai fechar alguma das ordens pai, SL e TP 
             devo verificar as ordens pendentes para cancela-las """

            # amount = open_trades[symbol]['amount'] # pego a quantidade de moeda comprada para emitir uma ordem e fechar a posição
            # Criar uma ordem de mercado para fechar a posição
        response = exchange.setMarginMode ('isolated', symbol.replace("/",""))   #, paramIs
        # print(f"{response} = exchange.setMarginMode ('isolated', symbol)")
        response = exchange.set_leverage(20,symbol.replace("/",""))
        amount = open_trades[symbol]['amount']
        osymbol = symbol.replace('/','')
        # amount_fecha = - amount   variavel não acessada comando inutil
        try:
            trade_side = "buy" if open_trades[symbol]['direction'] == "short" else "sell"
            # Criar uma ordem de mercado para fechar a posição
            order = exchange.create_order(
            symbol=osymbol,
            type='market',
            side=trade_side,
            amount=amount)
            attempts = 0
            max_attempts = 5
            while attempts < max_attempts:
                try:
                    order_sl = exchange.fetch_order(order['id'],osymbol)
                    if order_sl == order_sl: # order_sl['status'] == 'FILLED' or order_sl['status'] == 'filled':
                        open_trades[symbol]['exit_price'] = order['cost']
                        # fechado o trade cancela a ordem de stop_loss pendente.
                        exchange.cancel_order(open_trades[symbol]['sl_order_id'],osymbol)
                        attempts += 1
                        
                        break
                    else:
                        time.sleep(0.5)                       
                except Exception as e:
                    print(f"Error fetching order: {e}")


            
            
                # Implementar ações para lidar com ordens não executadas
            print("Posição fechada com sucesso.")
        except Exception as e:
            print(f"Erro ao fechar posição: {e}")
          #  print(f"{Fore.RED}Erro ao fechar posição {cancel_order_id} para {symbol} : {e}{Style.RESET_ALL}")
          #  app.log_message(f"Erro ao fechar posição {cancel_order_id} para {symbol} : {e}", "important")
        bina_open_orders = exchange.fetch_open_orders(symbol)
        print(f'len de bina+pend; {len(bina_open_orders)}')
        if len(bina_open_orders) >= 1:
            # se for igual a 1 é porque uma das pendentes ja executou. restou uma para ser cancelada
            for order_pend in bina_open_orders:
                if order_pend['symbol'] == symbol.replace("/","") :
                    try:
                        cancel_order_id = order_pend['id']
                        exchange.cancel_order(cancel_order_id, symbol.replace("/",""))
 
                    except Exception as erro:
                        print(f"{Fore.RED}Erro ao cancelar ordem {order_pend['id']} para {symbol} : {erro}{Style.RESET_ALL}")
                        app.log_message(f"Erro ao cancelar ordem {order_pend['id']} para {symbol} : {erro}", "important")
                        


        # print(f"Trade fechado para {symbol}. Detalhes da ordem: {close_order}")
   
        # atualizar lucro/prejuizo

        # app.log_message(f"{close_side}.\n")
        update_balance_inicial()
        # Remover o trade da lista de trades abertos
        # closed_trades[symbol] = open_trades[symbol]
        closed_trades_count += 1
        if open_trades[symbol]['direction'] == 'long':
            long_trades_count -= 1
            resultado = (open_trades[symbol]['exit_price']-open_trades[symbol]['open_price'])*(open_trades[symbol]['amount']*lev)

        else:
            resultado = (open_trades[symbol]['open_price']-open_trades[symbol]['exit_price'])*(open_trades[symbol]['amount']*lev)
            short_trades_count -= 1
        if resultado > 0:
            vol_lucro += resultado/100
        else:
            vol_preju += resultado/100
            
        app.log_message(f"Fecho trade para {symbol} : Resultado : {resultado}", "infoblue")
        #atualizar lucro/prejuízo

        if open_trades[symbol]['direction'] == 'long':
                app.trade_c_lucro_label.config(text=f"Lucro: {vol_lucro:.2f}",fg="green", font=("Helvetica", 12, "bold"))
        else:
            try:
                
                app.trade_c_prej_label.config(text=f" Preju: {vol_preju:.2f}",fg="red", font=("Helvetica", 12, "bold"))
            except Exception as errosh:
                print(f'errosh : {errosh}')
        # =============================================================
        open_trades.pop(symbol)
        app.close_trade_box(symbol)
        return    
            
# clase trade4real de desenvolvimento ======
class trade4real_desenv(TradeBase):

    # ======= FUNÇÃO PARA CHECKAR O STATUS DE ORDEM EMITIDA ========================
    def check_order_status(self, order_id, symbol):
        try:
            order = exchange.fetch_order(order_id, symbol)
            return order['status']
        except Exception as e:
            print(f"Erro ao verificar status da ordem: {e}")
            app.log_message(f"Erro ao verificar status da ordem:","important")
            app.log_message(f"{symbol}: order_id: {order_id} :  {e}")
            return None



        # Verificação de slippage (opcional)
        stop_loss_adjusted = round(stop_loss * (1 - slippage), precisionP)
        take_profit_adjusted = round(take_profit * (1 + slippage), precisionP)
        if stop_loss_adjusted >= stop_loss:
            raise ValueError("Stop Loss ajustado é maior que o valor original.")
        if take_profit_adjusted <= take_profit:
            raise ValueError("Take Profit ajustado é menor que o valor original.")
    #=========================OPEN TRADE REAL ======================================
    def open_trade(self, symbol, direction, price, stop_loss, take_profit):
        
        if max_trades <= (long_trades_count + short_trades_count) or stop_loss == take_profit:
            app.log_message(f"Limite máximo de {max_trades} trades atingido.\n")
            return
        
        if trade_size >= balance:
            app.log_message(f"Saldo insuficiente {trade_size} para saldo de : {balance}.\n")
            return
        
        # Determinar os lados da ordem
        if direction == 'long':
            trade_side = "buy"
            trade_SL, trade_TP = "sell", "sell"
        elif direction == 'short':
            trade_side = "sell"
            trade_SL, trade_TP = "buy", "buy"
        else:
            print(f"Erro na direção: {direction}")
            app.log_message(f"Erro na informação de direção do trade: {direction}.\n", "important")
            return  # Adicionando o return aqui para interromper a execução se a direção estiver incorreta
        
        amount = (trade_size * lev) / price
        print(f'Amount calculado: {amount}')
        otsymbol = symbol.replace('/','')
        # Obtenha a precisão permitida para o símbolo
        try:         
            
            precision = exchange.markets[symbol]['precision']['amount']
            # Calcule o número de casas decimais baseado na precisão
            decimal_places = len(str(precision).split('.')[1]) if '.' in str(precision) else 0

            # Arredonde a quantidade para a precisão correta
            amount = round(amount,decimal_places)
            #amount =  exchange.amount_to_precision(symbol, amount)
            precisionP = exchange.markets[symbol]['precision']['price']
            precisionP = len(str(precisionP).split('.')[1]) if '.' in str(precisionP) else 0

            stop_loss = float(exchange.price_to_precision(symbol,stop_loss))   #exchange.amount_to_precision(symbol, stop_loss)
            take_profit = float(exchange.price_to_precision(symbol,take_profit))  #exchange.amount_to_precision(symbol,take_profit)
        except Exception as err:
            print(f"erro no precision : {err} - saindo do trade")
            return


        
        # Configurar a margem isolada para o símbolo

        # symbol = symbol.replace('/', '')  # Certifique-se de remover a barra do símbolo para a Binance
        print(f"{Fore.RED} symbolo antes de mandar para margin: {symbol} e depois de alterado {symbol.replace('/','')}{Style.RESET_ALL}")

        
        """try:
            response = exchange.setMarginMode ('isolated', otsymbol)   #, paramIs
            # print(f"{response} = exchange.setMarginMode ('isolated', symbol)")
            response = exchange.set_leverage(20,otsymbol)
        except Exception as e:
            print(f"{Fore.RED}Erro ao configurar margem isolada: {e}{Style.RESET_ALL}")
            return """

        # Criar ordem de mercado
        preco_corrente,timestamp = fetch_current_price(symbol)
        stop_loss = float(exchange.price_to_precision(symbol,stop_loss))   #exchange.amount_to_precision(symbol, stop_loss)
        take_profit = float(exchange.price_to_precision(symbol,take_profit))  #exchange.amount_to_precision(symbol,take_profit)
        #self.validate_oco_order(direction, stop_loss, take_profit, preco_corrente,precisionP )
        # Cria a ordem de mercado
        print(f" symbol : {symbol} side: {trade_side} type : {'market'} amount: {amount } stop_loss: {stop_loss} stop_gain : {take_profit}")
        """order = exchange.create_order(
            symbol=otsymbol,
            type='market',
            side=trade_side,
            amount=amount)"""

  
        # Armazenar o ID da ordem
        order_id = random.randint(000000,999999) #  order['id']
        open_price = preco_corrente   # order['price'] # preço executado
        # comando abaixo seve voltar ao original
        # amount = order['amount']   # pegando a quantidade executada para passar para as outra ordens  pendentes
        open_trades[symbol]['order_id'] = order_id # order['id']
        inverted_side = 'sell' if trade_side == 'buy' else 'buy'
        # criar uma ordem OCO para SL e TP - se uma das duas executar fecha a posição e cancela a outra
        # se a posição for fechada manualmente, basta cancelar uma delas que a outra "morre" junto - isto é um teste
        stop_limit_price = stop_loss * (1 + 0.0031) if inverted_side == 'sell' else stop_loss * ( 1 - 0.0031)
        stop_limit_price = float(exchange.price_to_precision(symbol,stop_limit_price))
        try:
           
  
                 # 'reduceOnly': True  # Garante que a ordem só reduz a posição })

            A = 0 # só para manter o try
        # insere ordem de stop_loss a limite e guarda a order_id para posterior cancelamento.

            """   order_sl = exchange.create_order(
            symbol=symbol,
            type='stop_market',  # Tipo de ordem para o Stop Loss
            side=inverted_side,  # 'buy' se você estiver fechando uma posição short
            amount=amount,  # Mesma quantidade da posição de entrada
            params={'stopPrice': stop_loss, 'reduceOnly' : 'true'}  # Preço de stop (trigger)
            )"""

            # emitida a ordem de SL, guarda a order_id no open_trades 
            # open_trades[symbol]['sl_order_id'] = order_sl['id']
            #emissão da ordem de take profit ... 
            # Emite a ordem de Take Profit (a limite)
            """order_tp = exchange.create_limit_order(
                symbol=symbol,
                side=inverted_side,  # 'buy' se você estiver fechando uma posição short
                amount=amount,  # Mesma quantidade da posição de entrada
                price=take_profit,  # Preço alvo para o Take Profit
                params={'reduceOnly' : 'true'} 
            )"""
        # emitida a ordem de take_profit guardar no open_trades
        # open_trades[symbol]['tp_order_id'] = order_tp['id'] 

        except Exception as er:
            print (f'Erro na ordem  : {er}')
        # Verificando o status da ordem"""
        # order_info = exchange.fetch_order(order_id, symbol)    deve voltar ao normal
        print(f'{Fore.CYAN} Indormaçoes sobre ordem gerada ================================')
        app.log_message(f"Ordem {direction} aberta para {symbol} OrderId ={open_trades[symbol]['order_id']}","infoblue")
        #print(f"{order_info}{Style.RESET_ALL}")
        """if order_info['status'] == 'closed':
            # Obtendo o histórico da ordem
            order_history = exchange.fetch_order(order_id, symbol)
            amount = order_history['amount']
            # open_price = order_history['price']
            print(order_history['price'], order_history['amount'])  # Preço de execução da ordem e quantidade

            order_sl_hist = exchange.fetch_order(order_sl['id'], symbol)
            SL = order_sl_hist['triggerPrice']
            open_trades[symbol]['stop_loss'] = SL


            order_tp_hist = exchange.fetch_order(order_tp['id'], symbol)
            # take_profit = take_profit #order_tp_hist['price']
            open_trades[symbol] = {'open_order_id': order_id, 'symbol': symbol, 'direction' : direction, 'amount' : amount, 'open_price' : open_price, 'stop_loss': stop_loss, 'sl_order_id' : order_sl['id'] , 'stop_gain' : take_profit, 'tp_order_id' : order_tp['id']}  # Inicializando o dicionário de trades abertos corretamente
        """    
        app.log_message(f"{open_trades[symbol]['open_price']} sl : {open_trades[symbol]['stop_loss']} TP : {open_trades[symbol]['stop_gain']}","info")
        print(f"{Fore.MAGENTA}{open_trades[symbol]['open_price']} sl : {open_trades[symbol]['stop_loss']} TP : {open_trades[symbol]['stop_gain']}{Style.RESET_ALL}")
        
        #update_balance_inicial()   
    # Verificação para ordens de compra
        

            #balance = get_account_balance()
            #app.balance_label.config(text=f"${balance:.2f}")
            
        app.log_message(f"Trade aberto: {symbol}, Direção: {direction}, Preço: {price}, SL: {stop_loss}, TP: {take_profit}")
        app.open_new_trade_box(direction, symbol, price, stop_loss, take_profit, price)  # Atualizado o método

        return

    #============FUNÇÃO PARA CHECK SE EXISTEM ORDENS PENDENTES E CANCELA-LAS SE POSITIVO==================================================
    # Função para verificar e cancelar ordens pendentes
    def check_and_cancel_pending_orders(symbol, order_id_to_keep):
        open_orders = exchange.fetch_open_orders(symbol)
        for order in open_orders:
            if order['id'] != order_id_to_keep and order['symbol'] == symbol:
                try:
                    exchange.cancel_order(order['id'], symbol)
                    print(f"Ordem {order['id']} cancelada.")
                except Exception as e:
                    print(f"Erro ao cancelar a ordem {order['id']}: {e}")
    # ========== FUNÇÃO PARA FECHAR TRADES ATIVOS ============
    def close_trade(self, symbol, current_price, tsclose):
        global vol_lucro, vol_preju, closed_trades_count, short_trades_count, long_trades_count, closed_trades,\
        open_trades
        """
        Fecha uma posição aberta para o símbolo especificado.

        Args:
            symbol (str): O símbolo para o qual a posição deve ser fechada (por exemplo, 'BTC/USDT').
            direction (str): A direção do trade a ser fechado ('long' para posições compradas, 'short' para posições vendidas).
        """
        """ Entrei aqui pq algum evento fechou ou vai fechar alguma das ordens pai, SL e TP 
             devo verificar as ordens pendentes para cancela-las """
        # verifica se existe posição aberta para o symbol 
        # Obter o saldo da carteira
        # balance = exchange.fetch_balance()
      
            # amount = open_trades[symbol]['amount'] # pego a quantidade de moeda comprada para emitir uma ordem e fechar a posição
            # Criar uma ordem de mercado para fechar a posição
        amount = open_trades[symbol]['amount']
        osymbol = symbol.replace('/','')
        # amount_fecha = - amount   variavel não acessada comando inutil
        try:
            trade_side = "buy" if open_trades[symbol]['direction'] == "short" else "sell"
            # Criar uma ordem de mercado para fechar a posição
            """order = exchange.create_order(
            symbol=osymbol,
            type='market',
            side=trade_side,
            amount=amount)"""
            print("Posição fechada com sucesso.")
        except Exception as e:
            print(f"Erro ao fechar posição: {e}")
        #bina_open_orders = exchange.fetch_open_orders(symbol)
        bina_open_orders = ["01"]
        if len(bina_open_orders) == 1:
            # se for igual a 1 é porque uma das pendentes ja executou. restou uma para ser cancelada
            
            # =================================  cálculo do resultado ===================
            
            result = calcular_saldo(open_trades[symbol]['amount'],open_trades[symbol]['open_price'],current_price, lev, open_trades[symbol]['direction'] )
            # atualizaçao do label de resultado do trade
            val_semtradesiz = result - trade_size
            if val_semtradesiz > 0:
                vol_lucro += val_semtradesiz
                app.trade_c_lucro_label.config(text=f"Lucro: {vol_lucro:.2f}",fg="green", font=("Helvetica", 12, "bold"))
            else:
                try:
                    vol_preju += val_semtradesiz
                    app.trade_c_prej_label.config(text=f" Preju: {vol_preju:.2f}",fg="red", font=("Helvetica", 12, "bold"))
                except Exception as errosh:
                    print(f'errosh : {errosh}')
            # print(f"Trade fechado para {symbol}. Detalhes da ordem: {close_order}")
            total_trades_count += 1
            if open_trades[symbol]['direction']  == 'long':
                long_trades_count += 1
            else:
                short_trades_count += 1
            # closed_trades_count += 1  == esta la no close_trade_box
            app.log_message(f"Trade fechado para {symbol}:","infoblue") 
            # app.log_message(f"{close_side}.\n")
            # get_account_balance()
            # Remover o trade da lista de trades abertos
            closed_trades.append(open_trades[symbol])
            open_trades.pop(symbol)
            app.close_trade_box(symbol)
        return  


# ==========================================
class trade4fake(TradeBase):
    
    # Função para abrir um trade
    def open_trade(self, symbol, direction, price, stop_loss, take_profit):
        global open_trades, max_trades, trade_size,balance,ativo, long_trades_count, short_trades_count, \
            total_trades_count, df_abertos, precisao#
        if max_trades <= (long_trades_count+short_trades_count) and take_profit != stop_loss:
            app.log_message(f"Limite máximo de {max_trades} trades atingido.\n")
            return
        current_price, timestamp_ticker = fetch_current_price(symbol)
        casas_decimais = len(str(price).split(".")[1])

        take_profit = round(take_profit, casas_decimais)  #float(f"{take_profit:.{casas_decimais}}")
        stop_loss =  round(stop_loss, casas_decimais)   #float(f"{stop_loss:.{casas_decimais}}") 
        if  price == take_profit or price == stop_loss:
            print(f"{Fore.RED}  LARGUEI >>>{symbol}{Style.RESET_ALL}")
            app.log_message(f"Mensagem acima cancelada para symbol : {symbol}","important")

            trades_2_remove.append(symbol)
            black_list.append(symbol)
            return
        # Seja long ou short o trade_size vai ser descontado do saldo   (tem que ter margem)
        balance -= trade_size
        app.balance_label.config(text=f"${balance:.2f}")
        open_trades[symbol]['stop_loss'] = stop_loss
        open_trades[symbol]['stop_gain'] = take_profit
        app.log_message(f"Trade aberto: {symbol}, Direção: {direction}, Preço: {price}, SL: {stop_loss}, TP: {take_profit}","info")
        # app.create_trade_box(direction, symbol, price, stop_loss, take_profit, price)
        app.open_new_trade_box(direction, symbol, price, stop_loss, take_profit, current_price) #, open_trades[symbol]
        # app.update_counters(symbol,long_trades_count,short_trades_count, closed_trades_count )
        # update_open_trades()
        total_trades_count += 1
        if direction == 'long':
            long_trades_count += 1
        elif direction == 'short':
            short_trades_count += 1
        # assinar o symbol no websock
        #asyncio.create_task(subscribe_to_ticker(symbol))
        asyncio.run(subscribe_to_ticker(symbol))
        app.update_counters(symbol,total_trades_count,long_trades_count,short_trades_count, closed_trades_count )

    # Fechamento de trade ---- simulação ----
    def close_trade(self, symbol, current_price, tsclose, motivo = ""):
        global open_trades, closed_trades, closed_trades_count, trades_2_remove, long_trades_count, short_trades_count, max_trades, balance,total_trades_count
        global vol_lucro, vol_preju
        # trade = open_trades.pop(symbol, None)
        
        trades_2_remove.append(symbol)
        print("Vou excluir o sybol, que fechou do df_abertos")


        
        if symbol in open_trades.keys() : #and (symbol not in trades_2_remove):
            # ======= Adicionado para fazer update nos valores de encerramento do trade - close_price e timestamp_ticker
            open_trades[symbol]['close_price'] = current_price
            open_trades[symbol]['timestamp_close'] = tsclose
            
            # =================== 
            # =================================  cálculo do resultado ===================
            
            result = calcular_saldo(open_trades[symbol]['amount'],open_trades[symbol]['open_price'],current_price, lev, open_trades[symbol]['direction'] )
            # atualizaçao do label de resultado do trade
            val_semtradesiz = result - trade_size
            if val_semtradesiz > 0:
                vol_lucro += val_semtradesiz
                app.trade_c_lucro_label.config(text=f"Lucro: {vol_lucro:.2f}",fg="green", font=("Helvetica", 12, "bold"))
            else:
                try:
                    vol_preju += val_semtradesiz
                    app.trade_c_prej_label.config(text=f" Preju: {vol_preju:.2f}",fg="red", font=("Helvetica", 12, "bold"))
                except Exception as errosh:
                    print(f'errosh : {errosh}')
            print (f'{Fore.RED} %%%%%%%%%%%% Fechando trade : {symbol} %%%%%%%%%%%%%%%%%% {Style.RESET_ALL}')
            print(f'Vai atualizar o saldo com: {result} $$$$$$$$$$$$')
            app.update_balance(symbol, open_trades[symbol]["direction"], result)

        
            try:
                app.log_message(f"Trade Fechado: {symbol}\n", "important")
                app.log_message(f"Trade fechado: {symbol}, Resultado : {result}, Direção: {open_trades[symbol]['direction']}, Preço: {open_trades[symbol]['open_price']}, SL: {open_trades[symbol]['stop_loss']}")
            except Exception as e:
                print(f'Exception = {e} open_trades: {open_trades[symbol]}')

            if open_trades[symbol]['direction'] == 'long':
                long_trades_count -= 1
            else:
                short_trades_count -= 1
 
            app.update_counters(symbol,total_trades_count , long_trades_count,short_trades_count, closed_trades_count )
            app.close_trade_box(symbol)
            closed_trades.append(open_trades[symbol])
            open_trades.pop(symbol)



def simulate_trade(symbol, direction, timestamp, open_price, stop_loss, stop_gain, iWp): #, strategy
    global open_trades, total_trades_count, long_trades_count, short_trades_count,  max_trades, lev
    try:
        current_price,stop_loss, take_profit = calculo_sl_tp(symbol,df_abertos[symbol],True if direction == "long" else False)
        #print(f'{type(timestamp)}')
        print(f"current_price :{current_price} stop_loss:{stop_loss}, take_profit :{take_profit}")
        if  stop_loss == take_profit or open_price == take_profit:
            trades_2_remove.append(symbol)
            black_list.append(symbol)
            return
        precisao = exchange.markets[symbol]['precision']['price']
        precisao = len(str(precisao).split('.')[1]) if '.' in str(precisao) else 6
        if precisao == 0:
            precisao = 4
        open_trades[symbol] = {
            'symbol': symbol,
            'direction': direction,
            'timestamp': timestamp,
            'timestamp_close' : None,
            'open_price': open_price,
            'amount' : trade_size * 20 / open_price, # inserido 20 para a alavancagem 
            'close_price' : None,
            'valor_da_compra' : trade_size,  # Isso vai ser substituido pelo valor especificado no painel de inicio
            'stop_loss': stop_loss,
            'stop_gain': take_profit,
            'precisao' : precisao,
            'initialWallet': iWp,
            'reazon': None
        }
        try:
            print (f"precisao em open_trades :{open_trades[symbol]['precisao']}")
        except Exception as er:
            print(f"erro : {er}")
        try:
            open_trades[symbol]['amount'] = lev * trade_size / open_trades[symbol]['open_price']
        except Exception as erop:
            print (f'erro ao pesquisar preço corrente :{erop} no par:{symbol}')
        

        
        print(f'stop_gain de {symbol} : {open_trades[symbol]["stop_gain"]}')
    except Exception as e0:
        print(f'trade não estava aberto ainda. : {e0}')
    try:
        


        # app.log_trade(f"Trade aberto para {symbol}. Direção: {direction}, Preço de abertura: {open_price}, Stop Loss: {stop_loss}, \n Take Profit: {stop_gain} iWp: {iWp}, Timestamp: {timestamp}\n")
        # open_trades += 1
        # app.create_trade_box(direction, symbol, open_price, stop_loss, stop_gain, fetch_current_price(symbol))
        # update_open_trades()
        # Testa expectativa de lucro. Se for abaixo de 1% rejeita o trade
        dire = 'buy' if direction == 'long' else 'sell'
        # open_price,stop_loss,stop_gain = calculo_sl_tp()
        
        tcl.open_trade(symbol,direction, open_price, stop_loss, stop_gain)


    except Exception as errosimtra:
        print (f'Erro no simulado de trades: {errosimtra} *************************************************')
        tb = traceback.extract_tb(errosimtra.__traceback__)
        filename, line_number, function_name, text = tb[-1]
        app.log_message(f"Ocorreu um erro na linha {line_number} para {symbol} : do arquivo {filename}: {errosimtra}", "important")
        print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {errosimtra}")


# Função para fechar um trade simulacao
def close_trade_simulacao(symbol, current_price, tsclose, motivo):
    global open_trades, closed_trades, closed_trades_count, trades_2_remove, long_trades_count, short_trades_count, max_trades, balance,total_trades_count
    global vol_lucro, vol_preju
    # trade = open_trades.pop(symbol, None)
    
    trades_2_remove.append(symbol)
    print("Vou excluir o sybol, que fechou do df_abertos")


    
    if symbol in open_trades.keys() : #and (symbol not in trades_2_remove):
        # ======= Adicionado para fazer update nos valores de encerramento do trade - close_price e timestamp_ticker
        open_trades[symbol]['close_price'] = current_price
        open_trades[symbol]['timestamp_close'] = tsclose
        
        # =================== 
        # =================================  cálculo do resultado ===================
        
        result = calcular_saldo(open_trades[symbol]['amount'],open_trades[symbol]['open_price'],current_price, lev, open_trades[symbol]['direction'] )
        # atualizaçao do label de resultado do trade
        val_semtradesiz = result - trade_size
        if val_semtradesiz > 0:
            vol_lucro += val_semtradesiz
            app.trade_c_lucro_label.config(text=f"Lucro: {vol_lucro:.2f}",fg="green", font=("Helvetica", 12, "bold"))
        else:
            try:
                vol_preju += val_semtradesiz
                app.trade_c_prej_label.config(text=f" Preju: {vol_preju:.2f}",fg="red", font=("Helvetica", 12, "bold"))
            except Exception as errosh:
                print(f'errosh : {errosh}')
        print (f'{Fore.RED} %%%%%%%%%%%% Fechando trade : {symbol} %%%%%%%%%%%%%%%%%% {Style.RESET_ALL}')
        print(f'Vai atualizar o saldo com: {result} $$$$$$$$$$$$')
        app.update_balance(symbol, open_trades[symbol]["direction"], result)

        # app.update_balance_display()

        
        closed_trades[symbol] = open_trades[symbol]
        
 #       closed_trades[symbol]['reazon'] = motivo
        #closed_trades_count += 1
       
        try:
            app.log_message(f"Trade fechado: {symbol}, Resultado : {result}, Direção: {open_trades[symbol]['direction']}, Preço: {open_trades[symbol]['open_price']}, SL: {open_trades[symbol]['stop_loss']}, TP: {open_trades[symbol]['stop_gain']}")
        except Exception as e:
            print(f'Exception = {e} open_trades: {open_trades[symbol]}')
        if open_trades[symbol]['direction'] == 'long':
            long_trades_count -= 1
        else:
            short_trades_count -= 1
        # Não sei se isso esta certo mas acho que é por isso que tenta pegar preço para symbolos ja fechados
        # open_trades.pop(symbol)
        ###########  inserido acima me 11/8 as 00:20
        app.close_trade_box(symbol)
        # update_open_trades()
        total_trades_count -= 1
        # open_trades.pop(symbol)
        app.update_counters(symbol,total_trades_count , long_trades_count,short_trades_count, closed_trades_count )


def calculate_tr(high, low, close):
    return pd.DataFrame({'high': high, 'low': low, 'close': close}).apply(
        lambda x: max(x['high'] - x['low'], abs(x['high'] - x['close'].shift()), abs(x['low'] - x['close'].shift())),
        axis=1
    )
# Função para calcular indicadores
def calc_indicadores(dfe,current_price, symbol=None):
    
    # dfe['symbol'] = symbol

    try:
        """dfi = pd.DataFrame()
        dfi['TR'] = calculate_tr(dfe['high'], dfe['low'], dfe['close'])
        dfe['ATR'] = dfi['TR'].ewm(span=8, adjust=False).mean()"""
        calculo_natr = ta.atr(dfe['high'], dfe['low'], dfe['close'], window=12)
        dfe.loc[:,'ATR'] = ta.atr(dfe['high'], dfe['low'], dfe['close'], window=12)     # window 
        print (f"tail do atr : {dfe['ATR'].iloc[-1]}")
        """if dfe["ATR"].iloc[-1] < current_price * 1.1:
            print(f"ATR : {dfe['ATR'].iloc[-1]}")
            # dfe['ATR'].iloc[-1] = current_price * 1.1
            print(f"ATR após: {dfe['ATR'].iloc[-1]}")"""

    except Exception as eratr:
        print(f"Erro ao calcular atr: {eratr}")
        print(f"Tipo da exceção: {type(eratr)}")
        print(f"DataFrame columns: {dfe.columns}")
        print(f"Tipo de dados da coluna ATR: {dfe['ATR'].dtype}")

    # ==== calculo do vwap
    #dfe['vwap'] = ta.vwap(
    #    high=dfe['high'], 
    #    low=dfe['low'], 
    #    close=dfe['close'], 
    #    volume=dfe['volume'], 
    #    window=14  # janela de cálculo, pode ser ajustada conforme necessário
    #).volume_weighted_average_price()
    # mudei ao dfe['close'] pelo current_price pra ver qual a reação
    dfe.loc[:, 'highmax'] = 0
    dfe.loc[:, 'lowmax'] = 0
    dfe.loc[:, 'Engulfing'] = 0
    dfe.loc[:, 'sma7'] = dfe.ta.sma(close='close', length=7) #
    dfe.loc[:, 'ema42'] = ta.ema(close=dfe['close'], length=42)
    try:
        dfe.loc[:, 'ema28'] = dfe.ta.ema(close='close', length=26) # mudei para 26
    except Exception as erema28 :
       
        print (f' FOI AQUI : {erema28}')
    #dfe.loc[:, 'ema28'] = dfe.ta.ema(close='close', window=28) 
    # indicador de cruzamento de ema12 e ema21. n positivo ema12 sobre ema21 negativo ema21 sobre ema12 
    dfe.loc[:, 'cross_counter'] = 0 # definindo o campo no dataframe
    dfe.loc[:, 'cross_stoch'] = 0 # define cruzamento do estocastico no dataframe
    dfe.loc[:, 'psar_counter'] = 0
    dfe.loc[:, 'psar_dist'] = 0
    dfe.loc[:, 'MACD'] = 0
    dfe.loc[:, 'signal'] = 0
    # Calcular o Parabolic SAR
    # dfe['psar'] = float(0) 
    PSar = dfe.ta.psar(high='high',low='low', close='close', af=0.02, max_af=0.2)     #(high=dfe['high'], low=dfe['low'], close=dfe['close'], step=0.02, max_step=0.2)
    # calcular médias de 3 períodos das maximas e mínimas ============
    dfe.loc[:, '5max'] = dfe.ta.sma(close='high', length=3)
    dfe.loc[:, '5min'] = dfe.ta.sma(close='low', length=3)  #alterado de 3 para 9 para testes
    # ================================================================
    # Calculando o MACD usando a função ewm()
    dfe.loc[:,'MACD'] = dfe['close'].ewm(span=12, adjust=False).mean() - dfe['close'].ewm(span=26, adjust=False).mean()
    dfe.loc[:,'signal'] = dfe['MACD'].ewm(span=9, adjust=False).mean() 
    print(f"MACD :{dfe['MACD'].iloc[-3]} signal : {dfe['signal'].iloc[-3]}")
    # ==================== indicadores para estrategia richard dennis =================
    # long =========================
    #dfe['maximo_20_periodos'] = dfe['high'].rolling(window=20).max()
    #dfe['minimo_10_periodos'] = dfe['low'].rolling(window=10).min()
    # short ========================================================
    #dfe['minimo_20_periodos'] = dfe['low'].rolling(window=20).min()
    #dfe['maximo_10_periodos'] = dfe['high'].rolling(window=10).max()
    # ===========  fim do richard dennis ============================

    dfe.loc[:, 'psar'] = PSar['PSARl_0.02_0.2'].combine_first(PSar['PSARs_0.02_0.2'])
        # Calcular EMA9
    dfe.loc[:, 'ema12'] = dfe.ta.ema(close='close', length=9)   # mudei o window para ver a cara que fica ....
    
    
    dfe.loc[:, 'momentum'] = dfe.ta.roc(close='close', length=12)
    dfe.loc[:, 'mom_counter'] = 0
    try:
    #  Calculando SUPERtrend
        supertrend_df =ta.supertrend(high=dfe['high'], low=dfe['low'], close=dfe['close'], period=7, multiplier=3)
    # print(f'colunas do supertrend : {supertrend_df.columns}')
        dfe.loc[:,'SUPERtrend'] = supertrend_df.loc[:,'SUPERT_7_3.0']
    except Exception as er:
        print (f"erro no supertrend: {er}")
    #df.loc[:,'SUPERTrend'] = 
# Calculando MACD
    #MACD = dfe.ta.macd(close='close', fast=12, slow=26, signal=9)
    #dfe.loc[:, 'macd'] = MACD['MACD_12_26_9'] # linha MACD
    #dfe.loc[:, 'macds'] = MACD['MACDs_12_26_9']
# Calculando o Estocástico %K

    stochastic = dfe.ta.stoch('high', 'low', 'close', length=14, smooth_window=6)
    # print(f"stochastic: {stochastic.columns}")
    dfe.loc[:, '%K'] = stochastic['STOCHk_14_3_3']  # Nome da coluna pode variar dependendo da versão do pandas_ta
    dfe.loc[:, '%D'] = stochastic['STOCHd_14_3_3']  # Nome da coluna pode variar  #
    # Calculando o Estocástico %D (linha de sinal)
   
    # Iterar sobre o DataFrame para calcular o contador de cruzamentos de medias móveis e estocástico
    """try:
        for i in range(1, len(dfe)):
           #  print(f"dfe['ema12']: {dfe['ema12'].iloc[i]} dfe['ema28]: {dfe['ema28'].iloc[i]}")
            if dfe['ema12'].iloc[i] > dfe['ema28'].iloc[i] and dfe['ema12'].iloc[i-1] <= dfe['ema28'].iloc[i-1]:
                dfe.loc[i, 'cross_counter'] = 1
            elif dfe['ema12'].iloc[i] < dfe['ema28'].iloc[i] and dfe['ema12'].iloc[i-1] >= dfe['ema28'].iloc[i-1]:
                dfe.loc[i, 'cross_counter'] = -1
            else:
                dfe.loc[i, 'cross_counter'] = dfe.loc[i-1, 'cross_counter'] + (1 if dfe.loc[i-1,'cross_counter'] > 0 else -1)
            # ============================= estocástico ==============================================
            if dfe['%K'].iloc[i] > dfe['%D'].iloc[i] and dfe['%K'].iloc[i-1] <= dfe['%D'].iloc[i-1]:
                dfe.loc[i, 'cross_stoch'] = 1
            elif dfe['%K'].iloc[i] < dfe['%D'].iloc[i] and dfe['%K'].iloc[i-1] >= dfe['%D'].iloc[i-1]:
                dfe.loc[i, 'cross_stoch'] = -1
            else:
                dfe.loc[i, 'cross_stoch'] = dfe.loc[i-1, 'cross_stoch'] + (1 if dfe['cross_stoch'].iloc[i-1] > 0 else -1)
                # Verifica se houve cruzamento de zero
            if dfe['momentum'].iloc[i] > 0 and dfe['momentum'].iloc[i-1] <= 0:
                dfe.at[i, 'mom_counter'] = 1  # Define o contador como 1 na mudança de direção positiva
            elif dfe['momentum'].iloc[i] < 0 and dfe['momentum'].iloc[i-1] >= 0:
                dfe.at[i, 'mom_counter'] = -1  # Define o contador como -1 na mudança de direção negativa
            else:
                # Incrementa o contador com base na direção
                dfe.at[i, 'mom_counter'] = dfe.at[i-1, 'mom_counter'] + (1 if dfe['momentum'].iloc[i] > 0 else -1)
                # contador de psar
            if dfe['close'][i] > dfe['psar'][i] and dfe['psar_counter'][i-1] < 0:
                dfe.at[i, 'psar_counter'] = 1 
            elif dfe['close'][i] < dfe['psar'][i] and dfe['psar_counter'][i-1] > 0:
                dfe.at[i, 'psar_counter'] = -1
            else:
                dfe.at[i, 'psar_counter'] = 1 if dfe['close'][i] > dfe['psar'][i] else (-1 if dfe['close'][i] < dfe['psar'][i] else dfe.at[i-1, 'psar_counter'])
            dfe.at[i,'psar_dist'] = abs(dfe['psar'][i]-dfe['close'][i])
    except Exception as errcalc:
        print(f"Erro ao calcular indicador: {str(errcalc)}")
        tb = traceback.extract_tb(errcalc.__traceback__)
        filename, line_number, function_name, text = tb[-1]
        print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {errcalc}")"""
# INDICAÇÃO DE ENGOLFO ===================================
    # Engolfo de alta (bullish engulfing)
    cond_bullish = ((dfe['close'].shift(1) < dfe['open'].shift(1)) &  # Candle anterior de baixa
    (dfe['open'] < dfe['close']) &                                       # Candle atual de alta
    (dfe['open'] < dfe['close'].shift(1)) &                          # Abertura atual abaixo do fechamento anterior
    (dfe['close'] > dfe['open'].shift(1))  )                          # Fechamento atual acima da abertura anterior
                    
        # Engolfo de baixa (bearish engulfing)
    cond_bearish = ((dfe['close'].shift(1) > dfe['open'].shift(1)) &  # Candle anterior de alta
    (dfe['open'] > dfe['close']) &                    # Candle atual de baixa
    (dfe['open'] > dfe['close'].shift(1)) &           # Abertura atual acima do fechamento anterior
    (dfe['close'] < dfe['open'].shift(1))  )           # Fechamento atual abaixo da abertura anterior
        
        # Marcar os padrões no DataFrame
    dfe.loc[cond_bullish, 'Engulfing'] = 1
    dfe.loc[cond_bearish, 'Engulfing'] = -1
#========================================================

    #print(f'Dfe. columns : {dfe.columns}')
    #print (f"cross_counter do último candle: {dfe['cross_counter'].iloc[-1]}")
    return dfe


def testa_SL_TP(sym_sob_analise, current_price, symbol):
    global open_trades, stop_loss, ativo, max_trades, df_abertos, estrat
    
    
    current_price,timestamp_ticker = fetch_current_price(symbol)
    if open_trades[symbol]['direction'] == 'long':
                current_price, stop_loss, take_profit_price = calculo_sl_tp(symbol, df_abertos[symbol])

                open_trades[symbol]['stop_loss'] = stop_loss if open_trades[symbol]['stop_loss'] < stop_loss else open_trades[symbol]['stop_loss']
            
                # motivo = ""
                # condicoes_de_saida = condicao_short (df_abertos[symbol], current_price) #current_price <= sym_sob_analise['stop_loss'] 
                #print (f"open_trades stop_gain: {open_trades[symbol]['stop_gain']} current price ; {current_price}")
                # verificação se o par prescedente é um topo duplo c[-2] ~= o[-1] 
                #if padrao_candle (df_abertos[symbol]['close'].iloc[-2],df_abertos[symbol]['open'].iloc[-1]) and  df_abertos[symbol]['open'].iloc[-1] > df_abertos[symbol]['close'].iloc[-1]:
                #    print(f"{Fore.LIGHTBLUE_EX} topo duplo - long {timestamp_ticker}{Style.RESET_ALL}")
                    # app.log_message(f'Encontrou um provavel topo duplo em {symbol} no candle : {timestamp_ticker}', 'info')
                #print(f" {Fore.RED} comparação : {open_trades[symbol]['stop_gain'] <= current_price}{Style.RESET_ALL}")
                motivo = ""
                if open_trades[symbol]['stop_gain']  <= current_price: #!=  #
                    motivo = f'saida pelo stop_gain {current_price}'
                    # motivo = ""
                elif estrat.saida_long(df_abertos[symbol], current_price, symbol) : # or estrat.condicao_short(df_abertos[symbol], current_price):
                    motivo=f'saida pelos indicadores saida_long : {current_price} preço projetado: {open_trades[symbol]["stop_gain"]}'
                    app.log_message(f'Fecha trades long symbol: {symbol} current price : {current_price} timestamp : {timestamp_ticker} \n Motivo : {motivo} $$$$$$$$$$$$$$$$$$$$',"info")
                    # tcl.close_trade(symbol, current_price, timestamp_ticker, motivo)
                elif  current_price <= open_trades[symbol]['stop_loss']: 
                    motivo = f'saida pelo stop_loss {current_price}'
                    # motivo = ""
                  #and current_price <= open_trades[symbol]['stop_gain']) :  #  conds2 or   usar primeira condição de short para stop de long
                """else:            
                    if current_price > open_trades[symbol]['open_price'] :
                        # verificar pq dey erro na linha abaixo
                        #stop_loss = min( df_abertos[symbol]['ema12'].iloc[-1],df_abertos[symbol]['ema42'].iloc[-1], df_abertos[symbol]['ema28'].iloc[-1])  #current_price - 2.0*df['ATR'].iloc[-1] # estou mudando o stop_loss para:
                        current_price,stop_loss, take_profit = calculo_sl_tp(symbol, df_abertos[symbol])

                    # condicoes_de_saida =  (current_price <= sym_sob_analise['stop_gain'] or current_price >= sym_sob_analise['stop_loss']) or condicao_long(sym_sob_analise['symbol']) # or sym_sob_analise['open_price'] > sym_sob_analise['ema28']
                """
                    
 
                if motivo != "":
                    
                    open_trades[symbol]['close_price'] = current_price 
                    print('=======================================================================================================================')
                    try:
                        print(f'Fecha trades symbol: {symbol} resultado : {open_trades[symbol]["stop_loss"]} timestamp : {timestamp_ticker} \n Motivo : {motivo} $$$$$$$$$$$$$$$$$$$$ ') # Cruzamento Stoch : {sym_sob_analise["cross_stoch"]}')
                    except Exception as er:
                        print(f"erro no print : {er}" )
                        tb = traceback.extract_tb(er.__traceback__)
                        filename, line_number, function_name, text = tb[-1]
                        print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {er}")
                    print('=======================================================================================================================')
                    
                    app.log_trade(f'Fecha trades long symbol: {symbol} current price : {current_price} timestamp : {timestamp_ticker} \n Motivo : {motivo} $$$$$$$$$$$$$$$$$$$$')
                    tcl.close_trade(symbol, current_price, timestamp_ticker)
                if   stop_loss > open_trades[symbol]['stop_loss']:
                    open_trades[symbol]['stop_loss'] = stop_loss
                        
    # =============================================================================================================================
    elif open_trades[symbol]['direction'] == 'short':
        current_price, stop_loss, take_profit_price = calculo_sl_tp(symbol, df_abertos[symbol],False)

        motivo = ""
        
        """if open_trades[symbol]['stop_loss'] > stop_loss :
            open_trades[symbol]['stop_loss'] = stop_loss """
        #else:
            #open_trades[symbol]['stop_loss']
        # app.update_trade_box_labels(symbol,current_price, open_trades[symbol]['stop_loss'],open_trades[symbol]['stop_gain'])
                # condicoes_de_saida = condicao_short (df_abertos[symbol], current_price) #current_price <= sym_sob_analise['stop_loss'] 
        #if open_trades[symbol]['stop_gain'] <= current_price:
            #open_trades[symbol]['stop_gain'] = current_price * .988 # estipulando um profit de 1,2%
        # print(f" {Fore.RED} comparação : {open_trades[symbol]['stop_gain'] <= current_price}{Style.RESET_ALL}")
        #if padrao_candle (df_abertos[symbol]['close'].iloc[-2],df_abertos[symbol]['open'].iloc[-1]) and  df_abertos[symbol]['open'].iloc[-1] < df_abertos[symbol]['close'].iloc[-1]:
        #    print(f"{Fore.LIGHTBLUE_EX} topo duplo - short {symbol} {Style.RESET_ALL}")
            # app.log_message(f'Encontrou um provavel fundo duplo em {symbol} no candle : {timestamp_ticker}', 'info')
        if open_trades[symbol]['stop_gain'] != open_trades[symbol]['stop_gain'] : #>= current_price: # 
            motivo = f'saida pelo stop_gain {current_price}'
            # motivo = ""
        elif estrat.saida_short(df_abertos[symbol], current_price, symbol) : #or estrat.condicao_long(df_abertos[symbol], current_price):
            motivo=f'saida pelos indicadores : {current_price} preço projetado: {open_trades[symbol]["stop_gain"]}'
            app.log_message(f'Fecha trades long symbol: {symbol} current price : {current_price} timestamp : {timestamp_ticker} \n Motivo : {motivo} $$$$$$$$$$$$$$$$$$$$')
        #    tcl.close_trade(symbol, current_price, timestamp_ticker)
        elif  current_price >= open_trades[symbol]['stop_loss']: 
            motivo = f'saida pelo stop_loss {current_price}'
            motivo = ""
            #and current_price <= open_trades[symbol]['stop_gain']) :  #  conds2 or   usar primeira condição de short para stop de long
        #else:
            #current_price,stop_loss, take_profit = calculo_sl_tp(symbol, df_abertos[symbol] )
 
            # condicoes_de_saida =  (current_price <= sym_sob_analise['stop_gain'] or current_price >= sym_sob_analise['stop_loss']) or condicao_long(sym_sob_analise['symbol']) # or sym_sob_analise['open_price'] > sym_sob_analise['ema28']
           
            

        if motivo != "":
            
            open_trades[symbol]['close_price'] = current_price 
            print('=======================================================================================================================')
            try:
                print(f'Fecha trades symbol: {symbol} resultado : {open_trades[symbol]["stop_loss"]} timestamp : {timestamp_ticker} \n Motivo : {motivo} $$$$$$$$$$$$$$$$$$$$ ') # Cruzamento Stoch : {sym_sob_analise["cross_stoch"]}')
            except Exception as er:
                print(f"erro no print : {er}" )
                tb = traceback.extract_tb(er.__traceback__)
                filename, line_number, function_name, text = tb[-1]
                print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {er}")
            print('=======================================================================================================================')
            app.log_trade(f'Fecha trades long symbol: {symbol} current price : {current_price} timestamp : {timestamp_ticker} \n Motivo : {motivo} $$$$$$$$$$$$$$$$$$$$')
            tcl.close_trade(symbol, current_price, timestamp_ticker)
            print('=======================================================================================================================')
            motivo = ""
        if  stop_loss < open_trades[symbol]['stop_loss'] :
            open_trades[symbol]['stop_loss'] = stop_loss

    
    app.update_trade_box_labels(symbol, current_price, open_trades[symbol]['stop_loss'], open_trades[symbol]["stop_gain"])
    return
def atualiza_df_aberto(symbol):
    global df_abertos
    """if symbol not in df_abertos.keys() or symbol not in app.trade_boxes.keys():
        try:
            df_abertos.pop(symbol)
        except:
            return
        try:
            app.trade_boxes.pop(symbol)
        except:
            print(f"{symbol} Não estava no app.trade_boxes")
            return"""
    
    atudf = fetch_ohlcv(symbol,limit=1)
    if(symbol in trades_2_remove):
        if (symbol in df_abertos.keys()):
            df.abertos.pop(symbol)
        if (symbol in app.trade_boxes.keys()):
            app.close_trade_box(symbol)
            
    #print(f"atudf : {atudf['timestamp'].iloc[-1]} df_abertos: {df_abertos[symbol]['timestamp'].iloc[-1]} ")
    try:
        if atudf['timestamp'].iloc[-1] == df_abertos[symbol]['timestamp'].iloc[-1]:

            return
        else:
            # pega o total do histórico
            ohlcv_df = fetch_ohlcv(symbol)
            current_price,timestamp_ticker = fetch_current_price(symbol)
            # Calcular os indicadores
            ohlcv_df = calc_indicadores(ohlcv_df,current_price,symbols)

            # Atualizar o DataFrame de trades abertos, coluna por coluna
            for col in ohlcv_df.columns:
                df_abertos  = ohlcv_df[col]
    except Exception as e:
        print(f"Erro no atualiza_df_aberto {symbol}: {str(e)}")
        tb = traceback.extract_tb(e.__traceback__)
        filename, line_number, function_name, text = tb[-1]
        print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {e}")
        # calcular os indicadores para o acrescimo ao df_abertos


# Função para o loop do bot
def bot_loop():
    global max_trades, trade_size, long_trades_count, short_trades_count, ativo, trades_2_remove, running, symbols, usdt_markets, precisao, \
    df_abertos
    print('Entrou no boot_loop')
    # symbols = get_all_symbols()  # Obtém todos os símbolos disponíveis
    #print(f'Pegou todos os simbolos valor de ativo : {ativo} ')
    # ativo = True
    balance = get_account_balance()
    app.balance_label.config(text=f"${balance:.2f}")
    while ativo or (len(open_trades) >0):
        print(f'max_trades: {max_trades} long_trades_count:{long_trades_count}, short_trades_count:{short_trades_count}')
        #app.update_counters(symbol, long_trades_count, short_trades_count, closed_trades_count)
        if max_trades < (long_trades_count + short_trades_count):
                ativo = True
                print(f"Max trades reached, skipping {symbol}")
                # em vez do comando acima, colocar todos os simbolos dos trades abertos para que continuem sendo monitorados
                # tentativa de limpar os trades fechados aqui trades_2_remove
                for tr2rm in trades_2_remove:
                    open_trades.pop(tr2rm)
                
                symbols = open_trades.keys()
        #else:
           # ativo = False
           
        
        filtered_symbols = [symbol for symbol in symbols if symbol not in black_list]
        for symbol in filtered_symbols:
            #for symb in open_trades.keys():
            for symb in [key for key in open_trades.keys() if key not in trades_2_remove]:
                if not running:
                    break
                try:
                    #if symb not in open_trades.keys():
                        #e, timestamp_ticker = fetch_current_price(symb)
                    # dfbl = calc_indicadores(fetch_ohlcv(symb))
                    # dfbl = calc_indicadores(dfbl) # calcula os indicadores para o dfbl recem obtido
                    # open_trades[symb] = pd.merge(open_trades[symb], dfu, left_index=True, right_index=True, how='outer').fillna(0)
                    #if symb not in df_abertos.keys():
                    #    return
 
                    if symb in app.trade_boxes:
                        testa_SL_TP(df_abertos[symb],curr_price, symb)
                        #app.update_trade_box_labels(symb, curr_price, open_trades[symb]['stop_loss'],open_trades[symb]['stop_gain'])
                    #else:
                    #    print(f'Simbolo não existe no dicionario de trade_boxes : {symb}')
                    #    trades_2_remove.append(symb)
                    # Adiciona um delay de 200 milissegundos entre as leituras
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Erro ao obter preço para {symb}: {str(e)}")
                    tb = traceback.extract_tb(e.__traceback__)
                    filename, line_number, function_name, text = tb[-1]
                    print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {e}")
                    time.sleep(0.3)  # Delay maior em caso de erro para evitar bloqueio
             
            #===================================================================================  
            # Este trecho foi inserido para evitar baixar, calcular, e testar um symbol ja testado neste intervalo
            # Quando fechar o intervalo, baixa o histórico ,calcula os indices e analiza 
            #if symbol in last_timestamp.keys():
            #    last_timestamp[symbol] = last_candle['timestamp']
            last_candle = fetch_ohlcv(symbol,limit=1)
            
            try:
                curr_price,timestamp = fetch_current_price(symbol)
                if symbol not in last_timestamp.keys():
                    #adicao_last_timestamp = True
                    #print(f"colunas do last_candle : {last_candle.columns}")
                    #print(last_candle['timestamp'].dtype)

                    # Convertendo para datetime, se necessário
                    #last_candle['timestamp'] = pd.to_datetime(last_candle['timestamp'])
                    try:
                        last_timestamp[symbol] = last_candle['timestamp'].iloc[-1]
                        adicao_last_timestamp = True
                    except Exception as er:
                        
                        print(f"{Fore.RED} erro ao adquirir o ultimo candle: {symbol} - {er}{Style.RESET_ALL}")
                        trades_2_remove.append(symbol)
                        black_list.append(symbol)
                        #adicao_last_timestamp = False
                        #continueb
                if symbol not in df_abertos.keys() and symbol not in black_list:
                    df_abertos[symbol] = fetch_ohlcv(symbol)
                    #df = calc_indicadores(df_abertos[symbol],fetch_current_price(symbol)[0],symbol)
                if last_candle['timestamp'].iloc[-1] != last_timestamp[symbol] or adicao_last_timestamp :
                    adicao_last_timestamp = False

                    df = calc_indicadores(fetch_ohlcv(symbol),curr_price,symbol)
                    last_timestamp[symbol] = df['timestamp'].iloc[-1]
                # acho que aqui te que calcular indicadores ???????????????
                    if df.empty or (symbol in trades_2_remove) :
                        # print(f"No data for {symbol}")
                        if symbol in trades_2_remove and (long_trades_count + short_trades_count < max_trades):
                            print(f'Simbolo ja foi excluido: {symbol}')
                        continue
                    elif ativo and symbol not in open_trades.keys(): # and (max_trades < (long_trades_count + short_trades_count)):
                        print(f'Analisando par :{symbol}')
                        analyze_symbol(symbol, df)
            except Exception as e:
                    tb = traceback.extract_tb(e.__traceback__)
                    filename, line_number, function_name, text = tb[-1]
                    print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {e}")
                    print(f"erro no timestamp do last_candle (df vazio){symbol}: {e}")

            # ===================================================================================
        #Se tem trades a remover da lista de ativos, remove, sem afetar o loop de analize
        print(f'Fim do looping, antes de reiniciar deve remover todos os simboloa que estão trades_2_remov e open_trades')
        for removabel in trades_2_remove:
            if removabel in open_trades.keys():
                open_trades.pop(removabel,None)
            if removabel in app.trade_boxes.keys():
                app.trade_boxes.pop(removabel)

            print(f'Trades redtirados (fechados) : {removabel}')
        # print(f'open_trades : {open_trades}')
        
        trades_2_remove = []

def analyze_symbol (symbol, df):
    print(f'ENTROU EM ANALYZE_SYMBOL para {symbol}')
    # root.update()
    global open_trades, stop_loss, ativo, max_trades,  estrat
    print(f"Quantidades de trades abertos : {long_trades_count + short_trades_count}")
    """try:
        df = fetch_ohlcv(symbol)
    except Exception as errofetch:
        print(f' Erro ao fazer fetch de {symbol} : {errofetch}')
        return
    # print(f'Dados OHLCV obtidos para {symbol}') """
    try: 
        current_price, timestamp_ticker = fetch_current_price(symbol)
        
    except Exception as ee:
        # print(f'Erro ao obter current price inicio do analyze: {symbol} - {ee}  ERROERROERROERROERROERROERROERROERROERROERROERROERRO')
        black_list.append(symbol)
        return
    try:
        # print(f'Preço atual obtido para {symbol}: {current_price}')
        timestamp = df['timestamp'].iloc[-1]
        #df = calc_indicadores(df)
        # ==================================================================condções para long ===============================================
        
        iWp = ((df['ema12'].iloc[-1] - df['ema12'].iloc[-2])+  (df['%K'].iloc[-1] - df['%K'].iloc[-2]) + 2*(df['%K'].iloc[-1] - df['%D'].iloc[-1]) )/3

        # fim do para debu ===================================
        if symbol not in open_trades:
            # print(f'len de open_trades = {len(open_trades)}')
            if  max_trades > long_trades_count + short_trades_count and balance > trade_size:
                direcao = None  #vou usar para determinar se abro trade (simulate_trade)
                
                
                if estrat.condicao_long (df, current_price,symbol) : # condl1_1condl2 and condl3 and condl4
                    
                    current_price, stop_loss, stop_gain = calculo_sl_tp(symbol, df)
                    # validate_oco_order("long", stop_loss, stop_gain, current_price, None, None )
                    direcao = "long"
                    # 
                elif estrat.condicao_short (df, current_price, symbol) : # conds2 and conds4 and conds3 and conds1 : #and df['%K'].iloc[-1] >= 50 : # and (df['%D'].iloc[-1]/df['%K'].iloc[-1] ) >=  1 and (df['momentum'].iloc[-1] / df['momentum'].iloc[-2]) > 1 :                   # print(f'Condição de abertura de trade log satisfeita : {cond_short_lento}')
                    current_price, stop_loss, stop_gain = calculo_sl_tp(symbol, df, False)
                    # validate_oco_order("short", stop_loss, stop_gain, current_price, None, None )
                    direcao = "short"

                if direcao =='long' : #or direcao =='short':  
                    df_abertos[symbol] = df   #armazenar dataframe dos trades abertos com todos os indicadores
                    # verif_stop_loss = calculate_percentage_change(current_price, stop_loss, direcao)
                    # current_price, stop_loss, stop_gain = calculo_sl_tp(symbol,df,direcao)
                    current_price, stop_loss, stop_gain = calculo_sl_tp(symbol,df)
                    if stop_loss >= current_price:
                        stop_loss = stop_loss * 1.01
                        
                    simulate_trade(symbol, direcao, timestamp, current_price, stop_loss, stop_gain ,iWp) #,'Stochastic_SMA')
                    
                        
        else:
            print(f'entrou no teste para ajuste e fechamento para {symbol}')

            # ===========================================================================================================================
            
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        filename, line_number, function_name, text = tb[-1]
        print(f"Ocorreu um erro na linha {line_number} do arquivo {filename}: {e}")
        print(f"Erro ao analisar símbolo {symbol}: {e}")
    return True
# Função para iniciar o bot
def start_bot():
    global symbols, tcl
    print(f'Entrou no start_bot')
    global max_trades, max_trades_var, trade_size, estrat
    print(f'trade_size : {trade_size}')
    app.get_trade_size()   # pega o tamanho do trade.
    max_trades =  int(max_trades_var.get())  #int(balance / trade_size)
    max_trades_var.set = str(max_trades)
    # estrat = estrategia_lw9_4()
    #testar em qual tipo de funcionamento real ou simulado
    if app.trade_mode.get() == "REAL":
        tcl = trade4real()

        
    else:
        tcl = trade4fake()
        balance = 1000
    estrat =  estrategia_mix() # richarddennis() #  # estrategia_cross_ema12()#estratgia_super_trend() #
    symbols = get_all_symbols()  # tendar só classificar os simbolos uma vez -- não sei se é boa ideia .....
    schedule.every(2).seconds.do(bot_loop)
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(0.1)
    threading.Thread(target=run_scheduler).start()

if __name__ == "__main__":
    app = TradeManagerApp()
    print(' No main prestes a fazer um update_balance.... Pode ser aqui.')
    update_balance_inicial()
    app.mainloop()
    # estrat = estrategia_lw9_4()
    
