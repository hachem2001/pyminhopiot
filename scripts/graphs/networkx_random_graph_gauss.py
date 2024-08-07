import networkx as nx
from matplotlib import pyplot as plt
import random

"""

Generating some network graph that befits what we need
We define density the way we want here, though.

"""

density = 2
hearing_distance = 0.0001
n = 500
width = n**0.5 * hearing_distance
height = n**0.5 * hearing_distance

pos = {i: (random.gauss(0, width/density), random.gauss(0, height/density)) for i in range(n)}
G = nx.random_geometric_graph(n, dim=2, radius=hearing_distance, pos=pos)
largest_cc = G.subgraph(max(nx.connected_components(G), key=len)).copy()

print(largest_cc)
nodes = nx.draw(largest_cc, pos={i: G.nodes[i]['pos'] for i in (largest_cc.nodes)})
plt.show()
