import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


class SoilStrata:
    def __init__(self, file, soil_parameter_file):
        self.BH_log = pd.read_csv(file, index_col='info')
        self.soil_parameters = pd.read_csv(soil_parameter_file, index_col='info')


    def soil_thk_by_type(self, top_level, toe_level):
        soil_layer_top_level = self.BH_log['bottom_level'].shift(1)
        # 读取土层信息,计算各土层厚度：
        self.BH_log['soil_thk'] = soil_layer_top_level - self.BH_log['bottom_level']
        # 计算桩周土层厚度：
        judge_soil_layer_above_pile_top_level = (top_level < self.BH_log['bottom_level']) & (
                top_level < soil_layer_top_level)  # 判断某一层土的层顶和层底标高是否都高于桩顶标高
        judge_soil_layer_below_pile_toe_level = (toe_level > self.BH_log['bottom_level']) & (
                toe_level > soil_layer_top_level)  # 判断某一层土的层顶和层底标高是否都低于桩底标高
        self.BH_log['judge'] = judge_soil_layer_above_pile_top_level | judge_soil_layer_below_pile_toe_level  # 所有高于桩顶和低于桩底的桩侧土层，判断为False，否则为True
        judge = self.BH_log['judge'].values  # 将judge列转化为列表
        pile_top_list = []
        pile_toe_list = []
        for n in range(len(self.BH_log['bottom_level'])):
            pile_top_list.append(top_level)  # 创建一个列表，每个元素均为桩顶标高，列表长度为土层数
            pile_toe_list.append(toe_level)  # 创建一个列表，每个元素均为桩底标高，列表长度为土层数
        soil_layer_top_level_list = soil_layer_top_level.values  # 层顶标高转化为列表
        soil_layer_bottom_level_list = self.BH_log['bottom_level'].values  # 层底标高转化为列表
        top_level_array = np.array([pile_top_list, soil_layer_top_level_list])  # 将桩顶标高与土层层顶标高生成一个array
        bottom_level_array = np.array([pile_toe_list, soil_layer_bottom_level_list])  # 将桩底标高与土层层底标高生成一个array
        self.BH_log['soil_thk_around_pile'] = np.where(judge, 0, top_level_array.min(0) - bottom_level_array.max(0))  # 将a、b两个array竖向元素分别取小/取大，相减得到每层桩侧土层厚度
        return self.BH_log.groupby(['info']).sum()


class BoredPile:
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

    def compute_quk_with_strata(self, soil_strata: SoilStrata) -> pd.DataFrame:
        soil_thickness_by_type = soil_strata.soil_thk_by_type(self.top_level, self.toe_level)
        soil_thickness_by_type['skin_friction'] = soil_strata.soil_parameters['bored_pile_fsi'] * soil_thickness_by_type[
            'soil_thk_around_pile'] * 3.14 * self.dia # 计算并存储桩侧膜阻力于表格BH_soil_group中
        df3 = pd.DataFrame()
        df3['pile_tip_position'] = (self.toe_level >= soil_strata.BH_log['bottom_level']) & (
                self.toe_level <= soil_strata.BH_log['bottom_level'].shift(1))  # 判断桩底在哪一层土层中，生成一个布尔型列
        judge_2 = df3.groupby(['info']).any().values
        pile_tip_area = 3.14 * self.dia ** 2 / 4  # 计算桩端面积
        soil_thickness_by_type['tip_support_col'] = np.where(judge_2, 1, 0)  # 生成一列辅助列，系数桩端所在土层为1，其余为0
        soil_thickness_by_type['tip_capacity'] = soil_strata.soil_parameters['bored_pile_fp'] * pile_tip_area * soil_thickness_by_type[
            'tip_support_col']  # 计算桩端阻力列
        return soil_thickness_by_type['skin_friction'].sum() + soil_thickness_by_type['tip_capacity'].sum() #求单桩极限承载力


class Building:
    def __init__(self, upper_floors, basement_floors, area_per_floor, basement_area, upper_floor_load,
                 basement_floor_load):
        self.upper_floors = upper_floors
        self.basement_floors = basement_floors
        self.area_per_floor = area_per_floor
        self.basement_area = basement_area
        self.upper_floor_load = upper_floor_load
        self.basement_floor_load = basement_floor_load

# ------------------------------------------------Defined 2 Class above----------------------------------------------------


def compute_quks_with_all_BH_log(d_input, l, level_input): #计算特定桩径、桩长、桩顶标高的单桩承载力
    soil_parameters_file = 'soil_parameters.csv'
    bored_pile = BoredPile(d_input, l, level_input)

    pile_bhs = []
    pile_quks = []
    pile_ras = []
    for i in range(1, 999):
        bh_file = 'BH' + str(i) + '.csv'
        try:
            soil_strata = SoilStrata(bh_file, soil_parameters_file)
            quk = bored_pile.compute_quk_with_strata(soil_strata)
            pile_bhs.append(f'BH{i}')
            pile_quks.append(quk)
            pile_ras.append(quk / 2)
        except FileNotFoundError:
            return pile_bhs, pile_quks, pile_ras


def compute_all_pile_length_with_x_dia(L_min_input, L_max_input, D_input, level_input): #计算某桩长范围内，特定桩径、桩顶标高的单桩承载力
    summary_table_dia_x = pd.DataFrame({'BH': [], 'L': [], 'Quk': [], 'Ra': []})

    for l in range(L_min_input, L_max_input + 1, 1): #循环用户输入的最短～最长桩长范围，计算Ra
        bhs, quks, ras = compute_quks_with_all_BH_log(D_input, l, level_input)
        summary_table_dia_x = summary_table_dia_x.append(pd.DataFrame({
            'BH': bhs,
            'Quk': quks,
            'Ra': ras,
            'L': l
        }))#创建钻孔、桩长、Ra大表

    return summary_table_dia_x


def compute_all_dia(L_min_input, L_max_input, D_list, level_input): #计算某桩径列表内不同桩径，某桩长范围内、特定桩顶标高下的单桩承载力
    compute_all_dia_table = pd.DataFrame()

    for D in D_list:
        D_input = D
        summary_table_dia_x = compute_all_pile_length_with_x_dia(L_min_input, L_max_input, D_input,
                                                                   level_input)
        summary_table_dia_x.reset_index(drop=True, inplace=True)
        min_capacity_with_D_l = summary_table_dia_x[['L', 'Quk', 'Ra']].groupby(['L']).min() #根据L分组，找出Ra最小行，形成成果表（特定直径，不同桩长的Ra）
        min_capacity_with_D_l_dia_x = min_capacity_with_D_l['Ra'].values
        compute_all_dia_table['Dia=' + str(D_input)] = min_capacity_with_D_l_dia_x
    plt_table_index = range(L_min_input, L_max_input+1, 1)
    compute_all_dia_table['pile_length'] = plt_table_index
    compute_all_dia_table.set_index('pile_length', inplace=True)
    return compute_all_dia_table


def find_BH_for_min_pile_capacity(L_min_input, L_max_input, D_list, level_input):
    for D in D_list:
        D_input = D
        summary_table_dia_x = compute_all_pile_length_with_x_dia(L_min_input, L_max_input, D_input,
                                                                   level_input)
        summary_table_dia_x.reset_index(drop=True, inplace=True)
        find_min_row_id = summary_table_dia_x[['L', 'Quk', 'Ra']].groupby(['L']).idxmin() #根据L分组，找出Ra最小行行号，返回的是Dataframe
        min_id_list = find_min_row_id['Ra'].values #将Ra列(此时Ra列内元素为最小行行号)返回形成列表
        min_cap_BH_dic = {}
        for i in min_id_list:
            min_capacity_BH_log = compute_all_pile_length_with_x_dia(L_min_input, L_max_input, D_input,
                                                                   level_input)['BH'].iloc[i]
            pile_length_list = compute_all_pile_length_with_x_dia(L_min_input, L_max_input, D_input,
                                                                   level_input)['L'].iloc[i]
            min_cap_BH_dic['L=' + str(pile_length_list) + ', min pile capacity - BH log'] = min_capacity_BH_log
    return min_cap_BH_dic


def cost_analyze(unit_price, D_list, compute_all_dia_table, building: Building):
    total_load = building.area_per_floor * building.upper_floor_load * building.upper_floors + building.basement_area * \
                 building.basement_floors * building.basement_floor_load
    for D in D_list:
        compute_all_dia_table['Dia=' + str(D) +', total_pile_num'] = total_load / compute_all_dia_table['Dia=' + str(D)]
        compute_all_dia_table['Dia=' + str(D) + 'm, estimate cost'] = 3.14 * D**2 / 4 * \
                                                                      compute_all_dia_table.index * unit_price * \
                                                                      compute_all_dia_table['Dia=' + str(D) +
                                                                                            ', total_pile_num']
        compute_all_dia_table['Dia=' + str(D) + 'm, kN/estimate cost'] = \
             compute_all_dia_table['Dia=' + str(D)] * compute_all_dia_table['Dia=' + str(D) +', total_pile_num']\
             / compute_all_dia_table['Dia=' + str(D) + 'm, estimate cost']
    compute_all_dia_table.to_csv('compute_all_dia_table.csv')
    return compute_all_dia_table


#--------------------------------------Defined 3 basic method for compute pile capacity above---------------------------------


def plot_Ra_vs_L(input_table, D_list):
    fig, ax = plt.subplots(figsize=(5, 5), layout='constrained')
    for D in D_list:
        ax.plot(input_table.index, input_table['Dia=' + str(D)], 'o-', label='Dia=' + str(D))
    ax.set_xlabel('Pile Length')
    ax.set_ylabel('Ra')
    ax.set_title('Pile Length vs Ra - with Different Dia')
    ax.markers = ()
    ax.legend()
    plt.show()


def plot_cost_analyze(input_table, D_list):
    fig, ax = plt.subplots(figsize=(5, 5), layout='constrained')
    for D in D_list:
        ax.plot(input_table.index, input_table['Dia=' + str(D) + 'm, kN/estimate cost'], 'o-', label='Dia=' + str(D))
    ax.set_xlabel('Pile Length')
    ax.set_ylabel('kN/estimate cost (kN / W yuan)')
    ax.set_title('Pile Length vs kN/estimate cost - with Different Dia')
    ax.legend()
    plt.show()

#--------------------------------------Defined plotting method for pile capacity above---------------------------------



#--------------------------------------***用户输入区，调用函数***----------------------------------------------------------
core_table = compute_all_dia(60, 61, [0.6, 0.8, 1.0, 1.2], -3.1)
print(core_table)
plot_Ra_vs_L(core_table, [0.6, 0.8, 1.0, 1.2])

building = Building(26, 1, 472.81, 500, 15, 20)
cost_analyze_table = cost_analyze(0.15, [0.6, 0.8, 1.0, 1.2], core_table, building)
print(cost_analyze_table['Dia=0.6, total_pile_num'])
plot_cost_analyze(cost_analyze_table, [0.6, 0.8, 1.0, 1.2])

find_min_pile_cap_BH = find_BH_for_min_pile_capacity(60, 61, [0.6, 0.8, 1.0, 1.2], -3.1)
print(find_min_pile_cap_BH)

#--------------------------------------***用户输入区，调用函数***----------------------------------------------------------
