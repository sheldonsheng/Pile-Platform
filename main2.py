import pandas as pd


class SoilStrata:
    def __init__(self, file, soil_parameter_file):
        self.df = pd.read_csv(file, index_col='info')
        self.soil_parameters = pd.read_csv(soil_parameter_file, index_col='info')

    def soil_thk_by_type(self, top_level, toe_level):
        # 读取土层信息,计算各土层厚度：
        self.df['soil_thk'] = self.df['bottom_level'].shift(1) - self.df['bottom_level']
        # 计算桩周土层厚度：
        df1 = (top_level < self.df['bottom_level']) & (
                top_level < self.df['bottom_level'].shift(1))  # 判断某一层土的层顶和层底标高是否都高于桩顶标高
        df2 = (toe_level > self.df['bottom_level']) & (
                toe_level > self.df['bottom_level'].shift(1))  # 判断某一层土的层顶和层底标高是否都低于桩底标高
        self.df['judge'] = df1 | df2  # 所有高于桩顶和低于桩底的桩侧土层，判断为False，否则为True
        judge = self.df['judge'].values  # 将judge列转化为列表
        pile_top_list = []
        pile_toe_list = []
        for n in range(len(self.df['bottom_level'])):
            pile_top_list.append(top_level)  # 创建一个列表，每个元素均为桩顶标高，列表长度为土层数
            pile_toe_list.append(toe_level)  # 创建一个列表，每个元素均为桩底标高，列表长度为土层数
        bottom_level_list_shift1 = self.df['bottom_level'].shift(1).values  # 层顶标高转化为列表
        bottom_level_list = self.df['bottom_level'].values  # 层底标高转化为列表
        a = np.array([pile_top_list, bottom_level_list_shift1])  # 将桩顶标高与土层层顶标高生成一个array
        b = np.array([pile_toe_list, bottom_level_list])  # 将桩底标高与土层层底标高生成一个array
        self.df['soil_thk_around_pile'] = np.where(judge, 0, a.min(0) - b.max(0))  # 将a、b两个array竖向元素分别取小/取大，相减得到每层桩侧土层厚度
        return self.df.groupby(['info']).sum()


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
        df3['pile_tip_position'] = (self.toe_level >= soil_strata.df['bottom_level']) & (
                self.toe_level <= soil_strata.df['bottom_level'].shift(1))  # 判断桩底在哪一层土层中，生成一个布尔型列
        judge_2 = df3.groupby(['info']).any().values
        pile_tip_area = 3.14 * self.dia ** 2 / 4  # 计算桩端面积
        soil_thickness_by_type['tip_support_col'] = np.where(judge_2, 1, 0)  # 生成一列辅助列，系数桩端所在土层为1，其余为0
        soil_thickness_by_type['tip_capacity'] = soil_strata.soil_parameters['bored_pile_fp'] * pile_tip_area * soil_thickness_by_type[
            'tip_support_col']  # 计算桩端阻力列
        return soil_thickness_by_type['skin_friction'].sum() + soil_thickness_by_type['tip_capacity'].sum() #求单桩极限承载力


def compute_quks_for_bored_pile(d_input, l, level_input):
    soil_parameters_file = open('soil_parameters.csv', 'r')
    bored_pile = BoredPile(d_input, l, level_input)

    pile_bhs = []
    pile_quks = []
    pile_ras = []
    for i in range(1, 101):
        bh_file = open('BH' + str(i) + '.csv', 'r')
        soil_strata = SoilStrata(bh_file, soil_parameters_file)
        quk = bored_pile.compute_quk_with_strata(soil_strata)
        pile_bhs.append(f'BH{i}')
        pile_quks.append(quk)
        pile_ras.append(quk / 2)

    return pile_bhs, pile_quks, pile_ras


def compute_all(L_min_input, L_max_input, D_input, level_input):
    summary_table = pd.DataFrame({'BH': [], 'L': [], 'Quk': [], 'Ra': []})

    for l in range(L_min_input, L_max_input + 1, 1): #循环用户输入的最短～最长桩长范围，计算Ra
        bhs, quks, ras = compute_quks_for_bored_pile(D_input, l, level_input)
        summary_table = summary_table.append(pd.DataFrame({
            'BH': bhs,
            'Quk': quks,
            'Ra': ras,
            'L': l
        }))#创建钻孔、桩长、Ra大表

