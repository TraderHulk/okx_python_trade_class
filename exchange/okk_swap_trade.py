# -*- coding: utf-8 -*-

# Author : 'hxc'

# Time: 2022/11/14 5:21 PM

# File_name: 'okk_swap_trade.py'

"""
Describe: this is a demo!
"""
import re
import logging
import time
import sys
sys.path.append("../")

from exchange.okx import Account_api as Account
from exchange.okx import Market_api as Market
from exchange.okx import Trade_api as Trade
from exchange.okx import Public_api as Public
from exchange.okx import TradingBot_api as TradingBot
from decimal import Decimal


class okkSwap(object):
    """okk交易"""

    def __init__(self,api_key,secret_key,passphrase,flag='0'):
        self.marketAPI = Market.MarketAPI(api_key, secret_key, passphrase, False, flag)
        # trade api
        self.tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)
        # account api
        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)
        #public api
        self.publicAPI = Public.PublicAPI(api_key, secret_key, passphrase, False, flag="0")
        #TradingBotAPI
        self.tradingbotAPI = TradingBot.TradingBotAPI(api_key, secret_key, passphrase, False, flag)
        self.exchange_name = "okk"

    def set_lever(self,symbol,lever,mgnMode="cross"):
        """设置杠杆"""
        try:
            self.accountAPI.set_leverage(instId=symbol, lever=lever, mgnMode=mgnMode)
        except Exception as e :
            logging.info("设置杠杆失败")
            logging.info("{}".format(e))

    def timestamp_to_date(self, time_stamp, format_string="%Y-%m-%d %H:%M:%S"):
        time_stamp = int(time_stamp * (10 ** (10 - len(str(time_stamp)))))
        time_array = time.localtime(time_stamp)
        str_date = time.strftime(format_string, time_array)
        return str_date

    def get_kline_data(self,symbol,interval,after=None):
        """获取kline data"""
        if after:
            result = self.marketAPI.get_candlesticks(symbol, bar=interval,after=after)
        else:
            result = self.marketAPI.get_candlesticks(symbol, bar=interval, limit=500)

        kline_data = [
            {"symbol": symbol, "open": i[1], "high": i[2], "low": i[3], "close": i[4], "vol": i[5],
             "timestamp": i[0],
             "dt": self.timestamp_to_date(int(i[0]))}
            for i in reversed(result['data'])]

        return kline_data

    def get_instruments(self, symbol):
        """获取价格量的精度"""
        minSz = ""
        tickSz = ""
        try:
            r = self.publicAPI.get_instruments("SWAP", instId=symbol)
            data_info = r["data"][0]
            minSz = "0." + self.precision_from_string(data_info["minSz"]) * "0"
            tickSz = "0." + self.precision_from_string(data_info["tickSz"]) * "0"

        except Exception as e:
            print("获取{}精度出现问题".format(symbol))
            print(e)

        return minSz, tickSz

    def updateposition(self,symbol):
        """更新仓位信息"""

        position_dict = {"long":{"position":"0","open_price":"0","qty":"0","side":"","imr":"0"},
                         "short":{"position":"0","open_price":"0","qty":"0","side":"","imr":"0"}}

        try:
            time.sleep(1)
            result = self.accountAPI.get_positions('SWAP',symbol)

            if result['data'] != []:
                for i in result['data']:
                    if i['posSide'] == "long" and i['imr']:
                        position_dict['long']['open_price'] = i['avgPx'] if i['avgPx'] else "0"
                        position_dict['long']['position'] = "1" if i['avgPx'] else "0"
                        position_dict['long']['qty'] =i['availPos'] if i['availPos'] else "0"
                        position_dict['long']['side'] = i['posSide']
                        position_dict['long']['imr'] = i['imr'] if i['imr'] else "0"

                    elif i['posSide'] == "short" and i['imr']:

                        position_dict['short']['open_price'] = i['avgPx'] if i['avgPx'] else "0"
                        position_dict['short']['position'] = "-1" if i['avgPx'] else "0"
                        position_dict['short']['qty'] = i['availPos'] if i['availPos'] else "0"
                        position_dict['short']['side'] = i['posSide']
                        position_dict['short']['imr'] = i['imr'] if i['imr'] else "0"

        except Exception as e:
            logging.info("获取{}的仓位信息有问题:{}".format(symbol,str(e)))

        return position_dict



    def get_uid(self):
        """获取用户的uid"""
        uid = '-1'
        try:
            r = self.accountAPI.get_account_config()
            uid = r['data'][0]['uid']
        except Exception as e:
            logging.info("获取Uid失败")
            logging.info("{}".format(e))

        return uid

    def convert_contract_coin(self,symbol,qty,px,type='1',unit="coin"):
        """
        币张转化
        :param instId:
        :param sz: 币的数量
        :return:
        """
        qty_int = 0
        try:
            r=self.publicAPI.convert_contract_coin( instId=symbol,type=type,px=px, sz=qty,unit=unit)
            qty_int = r['data'][0]['sz']
            logging.info("获得开仓张数:{}".format(qty_int))
        except Exception as e:
            logging.info("币张转化有问题！！！qty:{}".format(qty))
        return qty_int




    def set_plan_order_algo(self,symbol,ordType, qty, side, posSide,triggerPx,triggerPxType="last",
                            tdMode="cross",clOrdId=None,reduceOnly=None):
        """进行策略下单计划委托下单"""
        algoId = "0"
        try:
            r =self.tradeAPI.place_algo_order(instId=symbol,
                                      tdMode=tdMode,
                                      side=side, #buy or sell
                                      ordType=ordType,  # 双向止盈止损 oco 移动止盈止损 move_order_stop 计划委托 trigger
                                      sz=qty,
                                      posSide=posSide, #long or short
                                      triggerPx=triggerPx,
                                      triggerPxType=triggerPxType,
                                      orderPx = "-1",
                                      clOrdId=clOrdId,
                                      reduceOnly=reduceOnly
                                      )


            algoId = r["data"][0]['algoId']
        except Exception as e:
            logging.info("{}下计划委托单失败：{}".format(symbol,e))

        return algoId


    def precision_from_string(self, string):
        parts = re.sub(r'0+$', '', string).split('.')
        return len(parts[1]) if len(parts) > 1 else 0

    def cancel_algo_order_list(self, symbol,algoid_list,ordType="trigger"):
        """取消策略订单"""

        if algoid_list:
            time.sleep(0.5)
            try:
                p = [{'algoId': i, 'instId': symbol, 'ordType': ordType} for i in algoid_list]
                r =self.tradeAPI.cancel_algo_order(p)
                logging.info("取消订单返回结果：{}".format(r))
            except Exception as e:
                logging.info("取消策略订单失败：{}".format(algoid_list))
                logging.info("{}".format(e))
                # print("过3秒... 进行再次取消")
                logging.info("过3秒... 进行再次取消")
                for i in algoid_list: self.tradeAPI.cancel_algo_order([{'algoId': i, 'instId': symbol,'ordType':ordType}])

    def cancel_order(self, symbol, id_list):
        """取消普通订单"""
        try:
            for i in id_list: self.tradeAPI.cancel_order(symbol, i)

        except Exception as e:
            print("取消普通订单失败")
            logging.info("取消普通订单失败")
            logging.info("{}".format(e))
            # print("过3秒... 进行再次取消")
            for i in id_list: self.tradeAPI.cancel_order(symbol, i)

    def set_pingall_order(self, symbol, posSide):
        """市场价全平"""
        try:
            r = self.tradeAPI.close_positions(instId=symbol,
                                              mgnMode="cross",
                                              posSide=posSide,
                                              ccy='')
            logging.info("{}市价全平成功".format(symbol))
        except Exception as e:
            logging.info("{}市价全平失败".format(symbol))
            # print("市价全平失败", symbol)
            logging.info("{}".format(e))

    def updatebalance(self):
        """更新一下资产信息"""
        usdt = 0.0
        try:
            result = self.accountAPI.get_account(ccy='USDT')
            print(result)
            u = result['data'][0]['totalEq']
            usdt = u
        except Exception as e:
            logging.info("获取资产信息失败")
            logging.info("{}".format(e))

        return float(usdt)

    def get_history_trade(self,symbol,instType="SWAP",ordType="market",state="canceled",limit="100"):
        """
        获取历史委托订单的成交情况
        :return:
        """
        try:
            r = self.tradeAPI.get_orders_history(instType=instType,ordType=ordType,instId=symbol,state=state,limit=limit)
            print(r)
        except Exception as e:
            logging.info("获取历史订单失败")
            logging.info("{}".format(e))













    def get_orderbook_bo(self,symbol):
        """获取订单簿深度"""
        asks_1, bids_1 = 0.0, 0.0
        try:
            # 获取产品深度  Get Order Book
            result = self.marketAPI.get_orderbook(instId=symbol,
                                             sz=20)
            asks_1 = float(result['data'][0]['asks'][0][0])
            bids_1 = float(result['data'][0]['bids'][0][0])

        except Exception as e:
            # print("获取订单簿失败")
            logging.info("获取订单薄失败")
            logging.info("{}".format(e))

        return asks_1, bids_1

    def set_duo_order(self,symbol, qty,ordType="market",tdMode="cross",px=None,reduceOnly=None):
        """设置多单"""
        code = '0'
        msg = "0"
        try:
            r=self.tradeAPI.place_order(instId=symbol,
                                          tdMode=tdMode,
                                          side='buy',
                                          posSide='long',
                                          ordType=ordType,
                                          px=px,
                                          sz=qty,
                                          reduceOnly=reduceOnly)

            code = r['code']
            msg = r['msg']

        except Exception as e:
            # print("下多单失败")
            logging.info("下多单失败")
            logging.info("{}".format(e))
        return code,msg

    def set_pingduo_order(self, symbol, qty, ordType="market", px=None, reduceOnly=True):
        """设置ping多单"""

        try:
            r = self.tradeAPI.place_order(instId=symbol,
                                          tdMode="cross",
                                          side='sell',
                                          posSide='long',
                                          ordType=ordType,
                                          px=px,
                                          sz=qty,
                                          reduceOnly=reduceOnly)
            print("平多:",r)


        except Exception as e:
            # print("平多单失败")
            logging.info("平多单失败")
            logging.info("{}".format(e))

    def set_kong_order(self, symbol, qty, ordType="market", tdMode="cross", px=None,
                      reduceOnly=None):
        """设置空单"""
        code = '0'
        msg = ""
        try:
            r = self.tradeAPI.place_order(instId=symbol,
                                      tdMode=tdMode,
                                      side='sell',
                                      posSide='short',
                                      ordType=ordType,
                                      px=px,
                                      sz=qty,
                                      reduceOnly=reduceOnly)

            code = r['code']
            msg = r['msg']

        except Exception as e:
            # print("下空单失败")
            logging.info("下空单失败")
            logging.info("{}".format(e))
        return code,msg

    def set_pingkong_order(self,symbol,qty,ordType="market",px=None,reduceOnly=True):
        """设置平空单"""
        try:
            r =self.tradeAPI.place_order(instId=symbol,
                                       tdMode="cross",
                                       side='buy',
                                       posSide='short',
                                       px=px,
                                       ordType=ordType,
                                       sz=qty,
                                       reduceOnly=reduceOnly
                                      )
            print("平空",r)
        except Exception as e:
            # print("下平空单失败")
            logging.info("下平空单失败")
            logging.info("{}".format(e))

    def update_no_trade_algo_orders(self, orderType,symbol):
        """获取所有止盈止损未成交订单"""
        no_trade__algo_orders_id_list_long = {}
        no_trade__algo_orders_id_list_short = {}
        try:
            time.sleep(0.5)
            result = self.tradeAPI.order_algos_list(orderType,instId=symbol, instType='SWAP')
            no_trade__algo_orders_id_list_long = {i["algoClOrdId"]: i["algoId"] for i in result['data'] if i['instId'] == symbol and i['posSide'] == "long"}
            no_trade__algo_orders_id_list_short =  {i["algoClOrdId"]: i["algoId"]for i in result['data'] if i['instId'] == symbol and i['posSide'] == "short" }
        except Exception as e:
            # print("获取所有止盈止损未成交订单失败")
            logging.info("{}获取所有止盈止损未成交订单失败".format(symbol))
            logging.info("{}".format(e))
        logging.info("未成交多单id:{}".format(no_trade__algo_orders_id_list_long))
        logging.info("未成交空单id:{}".format(no_trade__algo_orders_id_list_short))
        return no_trade__algo_orders_id_list_long,no_trade__algo_orders_id_list_short

    def update_no_trade_orders(self,orderType,symbol):
        """获取所有普通止盈止损的未成交的挂单"""

        no_trade_orders_id_list_long = []
        no_trade_orders_id_list_short = []
        try:
            result = self.tradeAPI.get_order_list(ordType=orderType)
            no_trade_orders_id_list_long = [i for i in result['data'] if
                                                  i['instId'] == symbol and i['posSide'] == "long"]
            no_trade_orders_id_list_short = [i for i in result['data'] if
                                                   i['instId'] == symbol and i['posSide'] == "short"]
        except Exception as e:
            # print("获取所有止盈止损未成交订单失败")
            logging.info("{}获取所有止盈止损未成交订单失败".format(symbol))
            logging.info("{}".format(e))
        return no_trade_orders_id_list_long, no_trade_orders_id_list_short

    def updatePosition(self):
        """更新仓位信息"""
        # r = self.publicAPI.convert_contract_coin(type='2', instId=symbol,
        #                                          sz=result['data'][1]['pos'])

        positionAmt = []
        try:
            result = self.accountAPI.get_positions('SWAP')

            if result['data'] != []:
                # print("dadadad",result["data"])
                logging.info("订单数据详情：{}".format(result["data"]))
                for i in result["data"]:
                    symbol = i['instId']

                    each_symbol_long = {"symbol": "", "positionSide": "", "positionAmt": 0, "leverage": 0,
                                        "entryPrice": 0.0, "userflag": "", "precition": "","usdt":0.0}
                    # each_symbol_short = {"symbol": "", "positionSide": "", "positionAmt": 0, "leverage": 0,
                    #                      "entryPrice": 0.0, "userflag": "", "precition": ""}
                    try:
                        if float(i['pos']) != 0:

                            each_symbol_long['symbol'] = symbol

                            # r = self.publicAPI.convert_contract_coin(type='2', instId=symbol, sz=i['pos'])

                            each_symbol_long['positionAmt'] = float(i['pos'])

                            # if "." not in i['pos']:
                            #     r = self.publicAPI.convert_contract_coin(type='1', instId=symbol, sz=i['pos'])
                            #     each_symbol_long['positionAmt'] = float(r['data'][0]['sz'])
                            #
                            # else:
                            #     each_symbol_long['positionAmt'] = float(i['pos'])

                            if i['posSide'] == "short":
                                each_symbol_long['positionAmt'] = -each_symbol_long['positionAmt']

                            each_symbol_long['positionSide'] = i['posSide']
                            each_symbol_long["unrealizedProfit"] = i["upl"]  # 未实现盈利
                            each_symbol_long['leverage'] = i['lever']
                            each_symbol_long['entryPrice'] =i['avgPx']
                            each_symbol_long["precition"] = "0." + self.precision_from_string(str(each_symbol_long['positionAmt'])) * "0"
                            positionAmt.append(each_symbol_long)

                    except Exception as e:
                        # print("1",e)
                        logging.info("{}".format(e))
                        pass


        except Exception as e:
            logging.info("OK 获取仓位失败")
            logging.info("{}".format(e))
            # logging.info("{}".format(e))

        # print("positionAmt", positionAmt)
        if positionAmt!="":
            logging.info("仓位数量{}".format(positionAmt))
        return  positionAmt

    def get_algo_order_status(self,algoClOrdId):
        """
        获取策略委托的单的信息
        :return: live 是 待生效，effective 已生效 canceled 已经撤销 order_failed
        """
        state = ""

        if algoClOrdId:
            time.sleep(0.5)
            try:
                r = self.tradeAPI.get_algo_order_details(algoClOrdId)

                state = r['data'][0]['state']
            except Exception as e:
                # print("获取所有止盈止损未成交订单失败")
                logging.info("获取未成交订单{}失败".format(algoClOrdId))
                logging.info("{}".format(e))

        return state






def grid_swap(self,symbol,sz,direction,lever,maxPx,minPx,girdNum,
                  tpTriggerPx,slTriggerPx,algoOrderType='contract_grid',runType='1',basePos=False):
        """"
        symbol:品种
        sz:投入保证金,单位为USDT
        direction:long：做多，short：做空，neutral：中性
        lever:杠杆倍数
        basePos:是否开底仓，默认为false
        maxPx:区间最高价
        minPx:区间最低价
        girdNum:网格的格数
        runType：网格下单类型，等差数列下单：1，等比数列：2 ，默认等差数列
        tpTriggerPx:止盈价格
        slTriggerPx:止损价格
        algoOrderType:网格类型：默认合约类型，grid表示现货网格
        """
        try:
            r = self.tradingbotAPI.grid_order_algo(
                instId=symbol,
                sz=sz,
                direction=direction,
                lever=lever,
                basePos=basePos,
                algoOrdType=algoOrderType,
                maxPx=maxPx,
                minPx=minPx,
                gridNum=girdNum,
                runType=runType,
                tpTriggerPx=tpTriggerPx,
                slTriggerPx=slTriggerPx)
            print("网格网格",r)
        except Exception as e:
            print("运行网格出问题")
            print(e)











if __name__ == "__main__":

    coin = "PEPE"
    api_key = "b1bdbc82-1-8165-8c5282b5447b"
    secret_key = "DD3400CEA1B48725CE9BB43439B41E54"
    passphrase = ""
    o = okkSwap(api_key,secret_key,passphrase)
    symbol = coin + "-USDT-SWAP"
    minSz, tickSz = o.get_instruments(symbol=symbol)  # 获取该币种的下单量精度 和price 精度

    print("{} 价格精度：{},下单量精度：{}".format(symbol, tickSz, minSz))
    qty_amount = 10 / float(0.0000078)
    print("下单量：",qty_amount)
    qty = o.convert_contract_coin(symbol=symbol,px=0.00000791, qty=qty_amount)  # 每一份所能下的张数
    print("张数：",qty)


















