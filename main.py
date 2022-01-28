# This is a simple platform for consultanting foundation design projects
# -*-coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib as plt
import math

#数据格式：孔口标高，各土层层底标高，如：
# BH1 = {'BH_level': 5.00, 'soil_layer1': 1.00, 'soil_layer2': 2.00, 'soil_layer3': 3.00}



class Bored_Pile:
    def __init__(self, dia, l, top_level):
        # 初始化灌注桩属性(直径、桩长)
        self.dia = dia
        self.l = l
        self.top_level = top_level
        self.toe_level = top_level - l


Pile = Bored_Pile(1, 20, 4.50)
#TODO: User Input

# 表1 - 后注浆桩侧增强系数、后注浆桩端增强系数下限
df_grout_lower = pd.DataFrame({'mud': [1.2, 0],'clay/silt': [1.4, 2.2], 'silty_sand/fine_sand': [1.6, 2.4],
                               'med_sand': [1.7, 2.6], 'coarse_sand': [2.0, 3.0], 'gravel': [2.4, 3.2],
                               'rock': [1.4, 2.0]}, index=['Bs', 'Bp'])

# 表2 - 后注浆桩侧增强系数、后注浆桩端增强系数上限
df_grout_upper = pd.DataFrame({'mud': [1.3, 0],'clay/silt': [1.8, 2.5], 'silty_sand/fine_sand': [2.0, 2.8],
                               'med_sand': [2.1, 3.0], 'coarse_sand': [2.5, 3.5], 'gravel': [3.0, 4.0],
                               'rock': [1.8, 2.4]}, index=['Bs', 'Bp'])

# 表3 - 尺寸效应系数桩侧、尺寸效应系数桩端
df_size_phi = pd.DataFrame({'clay/silt': [(0.8 / Pile.dia) ** (1/5), (0.8 / Pile.dia) ** (1/4)],
                            'sand/gravel': [(0.8 / Pile.dia) ** (1/3), (0.8 / Pile.dia) ** (1/3)]},
                           index=['Fs', 'Fp'])


def pile_capacity():
    try:
        f = open('soil_parameters.csv', 'r')
        soil_parameters = pd.read_csv(f, index_col='info')
    except FileNotFoundError:
        print("Please input a table of soil parameters in project file.")
#读取土层参数

    for i in range(1, 101):
        try:
            f = open('BH' + str(i) + '.csv', 'r')
            df = pd.read_csv(f, index_col='info')
#读取土层信息,计算各土层厚度：
            df['soil_thk']= df['bottom_level'].shift(1) - df['bottom_level']
#计算桩周土层厚度：
            df['judge_pile_top_level'] = (Pile.top_level > df['bottom_level']) & (Pile.top_level <= df['bottom_level'].shift(1))
            for value in df['judge_pile_top_level']:
                print(df['judge_pile_top_level'])
                print('--------------------------')
                if value == True:
                    print('True')
                    print('**********************')
                    # df['soil_thk_around_pile_1'] = Pile.top_level - df['bottom_level']
                # elif value == False:
                #     df['soil_thk_around_pile_1'] = df['bottom_level'].shift(1) - df['bottom_level']
            #判断桩顶位置

            df['judge_pile_toe_level'] = (Pile.toe_level < df['bottom_level'].shift(1)) & (Pile.toe_level >= df['bottom_level'])
            for value in df['judge_pile_toe_level']:
                if value:
                    df['soil_thk_around_pile_2'] = df['bottom_level'].shift(1) - Pile.toe_level
                else:
                    df['soil_thk_around_pile_2'] = df['bottom_level'].shift(1) - df['bottom_level']
            #判断桩底位置

            # print(df[['judge_pile_top_level', 'soil_thk_around_pile_1']])
            # print(df[['judge_pile_toe_level', 'soil_thk_around_pile_2']])
        except FileNotFoundError:
            pass

#todo:cal pile capacity of each pile


pile_capacity()










