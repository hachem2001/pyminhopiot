import networkx as nx
from matplotlib import pyplot as plt
import random

"""

Generating some network graph that befits what we need
We define density the way we want here, though.

"""

density = 1.5
hearing_distance = 30
n = 1000
width = n**(1/(density**2)) * hearing_distance * 1.5
height = n**(1/(density**2)) * hearing_distance / 1.5

pos = {i: (random.random() * width - width/2, random.random() * height - height/2) for i in range(n)}
G = nx.random_geometric_graph(n, dim=2, radius=hearing_distance, pos=pos)
largest_cc = G.subgraph(max(nx.connected_components(G), key=len)).copy()

print(largest_cc)
nodes = nx.draw(largest_cc, pos={i: G.nodes[i]['pos'] for i in (largest_cc.nodes)})
plt.show()
