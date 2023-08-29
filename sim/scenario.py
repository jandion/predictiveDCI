import os
import salabim as sim
import yaml
from collections import namedtuple, defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"), "r") as ymlfile:
    config = yaml.load(ymlfile, Loader=yaml.FullLoader)

class Processor(sim.Component):
    def setup(self, regular_store, offloading_store, parent_regular_store, parent_offloading_store, max_windows):
        self.regular_store = regular_store
        self.offloading_store = offloading_store
        self.parent_regular_store = parent_regular_store
        self.parent_offloading_store = parent_offloading_store
        self.max_windows = max_windows
        self.regular_window_time = defaultdict(lambda: 0)
        self.offloading_window_time = defaultdict(lambda: 0)
        self.regular_processor = RegularProcessor(store=self.regular_store, parent_regular_store=self.parent_regular_store, parent_offloading_store=self.parent_offloading_store, max_windows=self.max_windows, regular_window_time=self.regular_window_time, offloading_window_time=self.offloading_window_time)
        self.offloading_processor = OffloadingProcessor(store=self.offloading_store, parent_offloading_store=self.parent_offloading_store, max_windows=self.max_windows, regular_window_time=self.regular_window_time, offloading_window_time=self.offloading_window_time)

class RegularProcessor(sim.Component):
    
    def setup(self, store, parent_regular_store, parent_offloading_store, max_windows, regular_window_time, offloading_window_time):
        self.store = store
        self.parent_regular_store = parent_regular_store
        self.parent_offloading_store = parent_offloading_store
        self.max_windows = max_windows
        self.regular_window_time = regular_window_time
        self.offloading_window_time = offloading_window_time
        self.monitorLevel = sim.Monitor(name= f"{self.name()}_monitor",level=True)
        self.monitorLevel.monitor(True)

    def process(self):
        while True:
            ev = yield self.from_store(self.store)
            if self.parent_regular_store != None:
                self.to_store(self.parent_regular_store, Event(name=ev.name(), time=ev.time))
            if self.regular_window_time[ev.time] + self.offloading_window_time[ev.time] < self.max_windows:
                self.regular_window_time[ev.time] += 1
                self.monitorLevel.tally(self.regular_window_time[ev.time])
                Window(ev=ev)
            else:
                self.to_store(self.parent_offloading_store, ev)

class OffloadingProcessor(sim.Component):
    def setup(self, store, parent_offloading_store, max_windows, regular_window_time, offloading_window_time):
        self.store = store
        self.parent_offloading_store = parent_offloading_store
        self.max_windows = max_windows
        self.regular_window_time = regular_window_time
        self.offloading_window_time = offloading_window_time
        self.monitorLevel = sim.Monitor(name= f"{self.name()}_monitor",level=True)
        self.monitorLevel.monitor(True)
        
    def process(self):
        while True:
            ev = yield self.from_store(self.store)
            if self.regular_window_time[ev.time] + self.offloading_window_time[ev.time] < self.max_windows:
                self.offloading_window_time[ev.time] += 1
                self.monitorLevel.tally(self.offloading_window_time[ev.time])
                Window(ev=ev)
            else:
                self.to_store(self.parent_offloading_store, ev)

class Window(sim.Component):
    def setup(self, ev):
        self.ev = ev
    def process(self):
        yield self.hold(duration = config["processing_unit"]["window_duration"])

class Event(sim.Component):
    def setup(self, time):
        self.time = time
        
class EventGenerator(sim.Component):
    def setup(self, processing_unit):
        self.processing_unit = processing_unit
        self.event_count = 0
    def process(self):
        while True:
            yield self.hold(int(sim.Exponential(rate=config["event_generator"]["lambda"]).sample()))
            ev = Event(name=f"{self.name()}, ev{self.event_count}", time=env.now())
            self.event_count += 1
            self.to_store(self.processing_unit.regular_processor.store,ev)

# Create simulation environment

env = sim.Environment(trace=False, time_unit="seconds", random_seed=12345)
not_processed_events = sim.Store()
p_1 = Processor(name="P1", regular_store=sim.Store(), offloading_store=sim.Store(), parent_regular_store=None, parent_offloading_store=not_processed_events, max_windows=200)
p_1_1 = Processor(name="P1.1", regular_store=sim.Store(), offloading_store=sim.Store(), parent_regular_store=p_1.regular_store, parent_offloading_store=p_1.offloading_store, max_windows=20)
p_1_2 = Processor(name="P1.2", regular_store=sim.Store(), offloading_store=sim.Store(), parent_regular_store=p_1.regular_store, parent_offloading_store=p_1.offloading_store, max_windows=20)

p_1_1_1 = Processor(name="P1.1.1", regular_store=sim.Store(), offloading_store=sim.Store(), parent_regular_store=p_1_1.regular_store, parent_offloading_store=p_1_1.offloading_store, max_windows=10)
p_1_1_2 = Processor(name="P1.1.2", regular_store=sim.Store(), offloading_store=sim.Store(), parent_regular_store=p_1_1.regular_store, parent_offloading_store=p_1_1.offloading_store, max_windows=10)
p_1_2_1 = Processor(name="P1.2.1", regular_store=sim.Store(), offloading_store=sim.Store(), parent_regular_store=p_1_2.regular_store, parent_offloading_store=p_1_2.offloading_store, max_windows=10)
p_1_2_2 = Processor(name="P1.2.2", regular_store=sim.Store(), offloading_store=sim.Store(), parent_regular_store=p_1_2.regular_store, parent_offloading_store=p_1_2.offloading_store, max_windows=10)

def initializeEventGenerators(processing_unit, generators_per_unit=config["event_generator"]["generators_per_unit"]):
    for i in range(generators_per_unit):
        EventGenerator(processing_unit=processing_unit, name=processing_unit.name() + "_" + str(i))

initializeEventGenerators(p_1_1_1)
initializeEventGenerators(p_1_1_2)
initializeEventGenerators(p_1_2_1)
initializeEventGenerators(p_1_2_2)

# Run simulation

env.run(config["simmulation"]["duration"])

# Generate results chart

fig, ax = plt.subplots(2,1, figsize=(21,14))
df = pd.DataFrame( np.arange(0, config["simmulation"]["duration"]+1), columns =["t"])

df = df.merge(p_1_1_1.regular_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1_1_2.regular_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1_2_1.regular_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1_2_2.regular_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1_1.regular_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1_2.regular_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1.regular_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1.offloading_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1_1.offloading_processor.monitorLevel.as_dataframe(), how="left")
df = df.merge(p_1_2.offloading_processor.monitorLevel.as_dataframe(), how="left")
df.fillna(0, inplace=True)
df.columns = ["t", "P1.1.1", "P1.1.2", "P1.2.1", "P1.2.2", "P1.1", "P1.2", "P1", "P1_off", "P1.1_off", "P1.2_off"]

ax[1].plot(df["t"], df["P1.1.1"], drawstyle="steps-post")
ax[1].plot(df["t"], df["P1.1.2"], drawstyle="steps-post")
ax[1].plot(df["t"], df["P1.2.1"], drawstyle="steps-post")
ax[1].plot(df["t"], df["P1.2.2"], drawstyle="steps-post")
ax[1].plot(df["t"], df["P1.1"], drawstyle="steps-post", color="red")
ax[1].plot(df["t"], df["P1.2"], drawstyle="steps-post", color="green")
ax[1].plot(df["t"], df["P1"], drawstyle="steps-post", color="blue")

ax[1].set_xticks(np.arange(0, 100, 1))
ax[1].set_xticks(np.arange(0, 101, 10), minor=False)
ax[1].set_title("Regular units", fontsize=14)
ax[1].legend(["P1.1.1", "P1.1.2", "P1.2.1", "P1.2.2", "P1.1", "P1.2", "P1"], fontsize=14, loc="upper right")
ax[1].set_xlabel("Time", fontsize=14)
ax[1].set_ylabel("Windows", fontsize=14)


ax[0].plot(df["t"], df["P1_off"], drawstyle="steps-post", color="blue")
ax[0].plot(df["t"], df["P1.1_off"], drawstyle="steps-post", color="red")
ax[0].plot(df["t"], df["P1.2_off"], drawstyle="steps-post", color="green")

ax[0].set_xticks(np.arange(0, 100, 1))
ax[0].set_xticks(np.arange(0, 101, 10), minor=False)
ax[0].set_title("Offloading units",fontsize=14)
ax[0].legend(["P1.1", "P1.2", "P1"], fontsize=14, loc="upper right")
ax[0].set_xlabel("Time", fontsize=14)
ax[0].set_ylabel("Windows", fontsize=14)
if ax[0].get_ylim()[1] < 1:
    ax[0].set_ylim([0, 1])

fig.subplots_adjust(hspace=0.15,left=0.05,right=0.95,top=0.95,bottom=0.05)

#plt.show()

fig.savefig(f"sim_lambda_{config['event_generator']['lambda']}.svg")