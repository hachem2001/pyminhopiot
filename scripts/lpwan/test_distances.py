from piconetwork.lpwan_jitter import *

"""
Linear cluster test
"""

random.seed(1)

# Set loggers
EVENT_LOGGER.set_verbose(False)
GATEWAY_LOGGER.set_verbose(True)
NODE_LOGGER.set_verbose(True)
SIMULATOR_LOGGER.set_verbose(False)
SOURCE_LOGGER.set_verbose(True)
CHANNEL_LOGGER.set_verbose(True)

def node_cluster_around(x, y, number, radius):
    theta = 0
    nodes = []
    for i in range(number):
        theta = i * math.pi * 2 / number
        this_x = x + radius * math.cos(theta)
        this_y = y + radius * math.sin(theta)
        print(this_x, this_y)
        nodes.append(NodeLP(this_x, this_y))
    return nodes

def test_1():
    nodes = []

    source = SourceLP(0.0, 0.0, 50.0)
    nodes.append(source)

    nodes.append(NodeLP(1., .0))
    nodes.append(NodeLP(2., .0))
    nodes.append(GatewayLP(3., .0))

    nodes.append(NodeLP(0, 1.))
    nodes.append(NodeLP(0, 2.))
    nodes.append(GatewayLP(0, 3.))


    sim = Simulator(300, 0.1)

    # Assign simulator for every logger we want to keep track of time for
    for node in nodes:
        node.set_logger_simulator(sim)

    # Create channel
    channel = Channel(packet_delay_per_unit=0.001) # If delay per unit is too high, it will mess up all calculations. TODO : fix that.

    # Register all nodes to channel
    channel.create_metric_mesh(0.9, *nodes)

    # Add nodes to simulator
    sim.add_nodes(*nodes)

    # Start sending packets from source
    source.start_sending(sim)

    # Run the simulator
    sim.run()

def test_2():
    hearing_radius = 1.0
    nodes = []

    source = SourceLP(0.0, 0.0, 50.0)
    nodes.append(source)

    #nodes.extend(node_cluster_around(hearing_radius*1.5, 0.0, 2, hearing_radius/2.0))
    #nodes.append(GatewayLP(hearing_radius*3, .0))

    nodes.extend(node_cluster_around(0.0, hearing_radius*1.5, 4, hearing_radius/2.0))
    nodes.append(GatewayLP(.0, hearing_radius*3))

    sim = Simulator(300, 0.1)

    # Assign simulator for every logger we want to keep track of time for
    for node in nodes:
        node.set_logger_simulator(sim)

    # Create channel
    channel = Channel(packet_delay_per_unit=0.001) # If delay per unit is too high, it will mess up all calculations. TODO : fix that.

    # Register all nodes to channel
    channel.create_metric_mesh(hearing_radius, *nodes)

    # Add nodes to simulator
    sim.add_nodes(*nodes)

    # Start sending packets from source
    source.start_sending(sim)

    # Run the simulator
    sim.run()


if __name__ == '__main__':
    test_2()