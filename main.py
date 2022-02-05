# This is a simple platform for consultanting foundation design projects
# -*-coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math


# 数据格式：孔口标高，各土层层底标高，如：
# BH1 = {'BH_level': 5.00, 'soil_layer1': 1.00, 'soil_layer2': 2.00, 'soil_layer3': 3.00}

# 表1 - 后注浆桩侧增强系数、后注浆桩端增强系数下限
df_grout_lower = pd.DataFrame({'mud': [1.2, 0], 'clay/silt': [1.4, 2.2], 'silty_sand/fine_sand': [1.6, 2.4],
                               'med_sand': [1.7, 2.6], 'coarse_sand': [2.0, 3.0], 'gravel': [2.4, 3.2],
                               'rock': [1.4, 2.0]}, index=['Bs', 'Bp'])

# 表2 - 后注浆桩侧增强系数、后注浆桩端增强系数上限
df_grout_upper = pd.DataFrame({'mud': [1.3, 0], 'clay/silt': [1.8, 2.5], 'silty_sand/fine_sand': [2.0, 2.8],
                               'med_sand': [2.1, 3.0], 'coarse_sand': [2.5, 3.5], 'gravel': [3.0, 4.0],
                               'rock': [1.8, 2.4]}, index=['Bs', 'Bp'])

Pile_length_list = []
Quk_list = []
Ra_list = []
BH = []


class Bored_Pile:
    def __init__(self, dia, l, top_level):
        # 初始化灌注桩属性(直径、桩长)
        self.dia = dia
        self.l = l
        self.top_level = top_level
        self.toe_level = top_level - l
        # 表3 - 尺寸效应系数桩侧、尺寸效应系数桩端
        df_size_phi = pd.DataFrame({'clay/silt': [(0.8 / self.dia) ** (1 / 5), (0.8 / self.dia) ** (1 / 4)],
                                    'sand/gravel': [(0.8 / self.dia) ** (1 / 3), (0.8 / self.dia) ** (1 / 3)]},
                                   index=['Fs', 'Fp'])

    def pile_capacity(self):
        try:
            f = open('soil_parameters.csv', 'r')
            soil_parameters = pd.read_csv(f, index_col='info')
        except FileNotFoundError:
            print("Please input a table of soil parameters in project file.")
        # 读取土层参数
        for i in range(1, 101):
            try:
                f = open('BH' + str(i) + '.csv', 'r')
                df = pd.read_csv(f, index_col='info')
                # 读取土层信息,计算各土层厚度：
                df['soil_thk'] = df['bottom_level'].shift(1) - df['bottom_level']
                # 计算桩周土层厚度：
                df1 = (self.top_level < df['bottom_level']) & (
                            self.top_level < df['bottom_level'].shift(1))  # 判断某一层土的层顶和层底标高是否都高于桩顶标高
                df2 = (self.toe_level > df['bottom_level']) & (
                            self.toe_level > df['bottom_level'].shift(1))  # 判断某一层土的层顶和层底标高是否都低于桩底标高
                df['judge'] = df1 | df2  # 所有高于桩顶和低于桩底的桩侧土层，判断为False，否则为True
                judge = df['judge'].values  # 将judge列转化为列表
                pile_top_list = []
                pile_toe_list = []
                for n in range(len(df['bottom_level'])):
                    pile_top_list.append(self.top_level)  # 创建一个列表，每个元素均为桩顶标高，列表长度为土层数
                    pile_toe_list.append(self.toe_level)  # 创建一个列表，每个元素均为桩底标高，列表长度为土层数
                bottom_level_list_shift1 = df['bottom_level'].shift(1).values  # 层顶标高转化为列表
                bottom_level_list = df['bottom_level'].values  # 层底标高转化为列表
                a = np.array([pile_top_list, bottom_level_list_shift1])  # 将桩顶标高与土层层顶标高生成一个array
                b = np.array([pile_toe_list, bottom_level_list])  # 将桩底标高与土层层底标高生成一个array
                df['soil_thk_around_pile'] = np.where(judge, 0, a.min(0) - b.max(0))  # 将a、b两个array竖向元素分别取小/取大，相减得到每层桩侧土层厚度
                BH_soil_group = df.groupby(['info']).sum()  # 创建新表格BH_soil_group，将同名土层归类，层厚求和
                BH_soil_group['skin_friction'] = soil_parameters['bored_pile_fsi'] * BH_soil_group[
                    'soil_thk_around_pile'] * 3.14 * self.dia # 计算并存储桩侧膜阻力于表格BH_soil_group中
                df3 = pd.DataFrame()
                df3['pile_tip_position'] = (self.toe_level >= df['bottom_level']) & (
                            self.toe_level <= df['bottom_level'].shift(1))  # 判断桩底在哪一层土层中，生成一个布尔型列
                judge_2 = df3.groupby(['info']).any().values
                pile_tip_area = 3.14 * self.dia ** 2 / 4  # 计算桩端面积
                BH_soil_group['tip_support_col'] = np.where(judge_2, 1, 0)  # 生成一列辅助列，系数桩端所在土层为1，其余为0
                BH_soil_group['tip_capacity'] = soil_parameters['bored_pile_fp'] * pile_tip_area * BH_soil_group[
                    'tip_support_col']  # 计算桩端阻力列
                Quk = BH_soil_group['skin_friction'].sum() + BH_soil_group['tip_capacity'].sum() #求单桩极限承载力
                BH.append('BH' + str(i))
                Pile_length_list.append(self.l)
                Quk_list.append(Quk)
                Ra_list.append(Quk / 2)
                single_table = pd.DataFrame({'BH': BH, 'L': Pile_length_list, 'Quk': Quk_list, 'Ra': Ra_list})
            except FileNotFoundError:
                return single_table


def pile_length_analyze(L_min_input, L_max_input, D_input, level_input): #对指定桩径、不同桩长，进行承载力计算分析
    for l in range(L_min_input, L_max_input + 1, 1): #循环用户输入的最短～最长桩长范围，计算Ra
        table = Bored_Pile(D_input, l, level_input).pile_capacity()
        summary_table = pd.DataFrame({'BH': [], 'L': [], 'Quk': [], 'Ra': []})
        summary_table = summary_table.append(table)#创建钻孔、桩长、Ra大表

    print('-------Summary_Table-------')
    print(summary_table)
    Ra_min = summary_table.groupby('L').apply(lambda t: t[t.Ra == t.Ra.min()]) #找出每种桩长对应最小Ra，并列表，要求能够显示最小值对应的BH
    print('-------Ra_min_Table--------')
    print(Ra_min)
    plt_Ra_vs_L = pd.DataFrame(Ra_min.loc[:, ['L', 'Ra']].values) #提取groupby返回结果中的两列，并重新转化为Dataframe以去除multipleindex
    plt_Ra_vs_L.columns = ['L', 'Ra'] #指定列名
    plt_Ra_vs_L.set_index(['L'], inplace=True) #指定index
    plt_Ra_vs_L.plot() #打印图表
    plt.show()


D_list_user_input = [0.6, 0.8, 1, 1.2]
L_min_user_input = 18
L_max_user_input = 20
level_user_input = 4.5
# todo: 用户输入初始桩径、桩长、桩顶标高


def Ra_D_L_analyze():
    for D in D_list_user_input:
        print('Dia=' + str(D))
        pile_length_analyze(L_min_user_input, L_max_user_input, D, level_user_input)
        global Pile_length_list
        Pile_length_list = []
        global Quk_list
        Quk_list = []
        global Ra_list
        Ra_list = []
        global BH
        BH = []

Ra_D_L_analyze()