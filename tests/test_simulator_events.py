import unittest
import main


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, True)  # add assertion here

        # Example of usage:
        def event_callback(simulator: Simulator, event_name: str):
            print(f"Event '{event_name}' executed at time {simulator.current_time}")
            # Schedule a new event 2 time units later
            if simulator.current_time < 10:
                simulator.schedule_event(2, event_callback, f"Spawned by {event_name}")

        # Create a simulator instance
        sim = Simulator()

        # Schedule initial events
        sim.schedule_event(1, event_callback, "Initial Event 1")
        sim.schedule_event(3, event_callback, "Initial Event 2")

        # Run the simulator
        sim.run()


if __name__ == '__main__':
    unittest.main()
