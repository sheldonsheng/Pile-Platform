# This is a simple platform for consultanting foundation design projects
import pandas as pd
import numpy as np
import matplotlib as plt


class Bored_Pile:
    def __init__(self, dia, l):
        #初始化灌注桩属性(直径、桩长)
        self.dia = dia
        self.l = l

df_grout_phi = pd.DataFrame({''})

#表1 - 后注浆桩侧增强系数、后注浆桩端增强系数、
df_size_phi = pd.DataFrame({'clay/silt': [(0.8/Bored_Pile.dia)^(1/5), (0.8/Bored_Pile.dia)^(1/4)]}, \n
)
#表2 - 尺寸效应系数桩侧、尺寸效应系数桩端