from graphviz import Graph

g = Graph('G', filename='cluster.gv')

# NOTE: the subgraph name needs to begin with 'cluster' (all lowercase)
#       so that Graphviz recognizes it as a special cluster subgraph

# with g.subgraph(name='cluster_0') as c:
#     c.attr(style='filled', color='lightgrey')
#     c.node_attr.update(style='filled', color='white')
#     c.edges([('a0', 'a1'), ('a1', 'a2'), ('a2', 'a3')])
#     c.attr(label='process #1')

# with g.subgraph(name='cluster_1') as c:
#     c.attr(color='blue')
#     c.node_attr['style'] = 'filled'
#     c.edges([('b0', 'b1'), ('b1', 'b2'), ('b2', 'b3')])
#     c.attr(label='process #2')
g.attr('edge', len="0.1")
g.attr('node', shape='box', width="1.5", height="0.9")
g.attr('node', fontsize="14pt")
g.node('left schema')
g.node('right schema')

g.attr('node', shape='oval', width="0.5", height="0.5")
g.attr('node', fontsize="10pt")
g.node('input 0')
g.node('input 1')
g.node('input 2')
g.attr('node', shape='circle')
g.node('xor 0')
g.node('xor 1')


g.attr('node', shape='oval', width="1")
g.node('or')


g.edge('input 0', 'left schema')
g.edge('input 1', 'left schema')
g.edge('input 2', 'left schema')

g.edge('input 0', 'right schema')
g.edge('input 1', 'right schema')
g.edge('input 2', 'right schema')

g.edge('left schema', 'xor 0')
g.edge('left schema', 'xor 1')

g.edge('right schema', 'xor 0')
g.edge('right schema', 'xor 1')

g.edge('xor 0', 'or')
g.edge('xor 1', 'or')

g.view()
g.render(filename='miter')
