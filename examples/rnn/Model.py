import torch
from torch import nn
from torch.distributions.normal import Normal


class MarketPredictor(torch.nn.Module):

	def __init__(self, input_channels=4, recurrent=True):
		super().__init__()
		self.recurrent = recurrent
		# Parameters
		self.finput_layer_sizes = [input_channels, 8, 16, 16]
		self.foutput_layer_sizes = [16, 16, 8, 3]
		# Networks
		self.finput = self.create_net(layer_sizes=self.finput_layer_sizes)
		self.foutput = self.create_net(layer_sizes=self.foutput_layer_sizes, omit_last_activation=True)
		if self.recurrent:
			self.gru = nn.GRUCell(self.finput_layer_sizes[-1], self.finput_layer_sizes[-1])


	def create_net(self, layer_sizes, omit_last_activation=False):
		layers = []
		for i in range(len(layer_sizes)-1):
			layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))
			layers.append(nn.BatchNorm1d(layer_sizes[i+1]))
			if i < len(layer_sizes)-2 or not omit_last_activation:
				layers.append(nn.ReLU())
		return nn.Sequential(*layers)


	def forward(self, x):
		# x: batch x time x channels
		if self.recurrent:
			batch, timesteps, channels = x.shape
			x_input = self.finput(x.float().reshape(batch * timesteps, channels)).reshape(batch, timesteps, self.finput_layer_sizes[-1])
			hidden = torch.zeros(batch, self.finput_layer_sizes[-1])
			for t in range(timesteps):
				hidden = self.gru(x_input[:,t,:], hidden)
			x_output = self.foutput(hidden)
			return nn.functional.softmax(x_output, dim=1)
		else:
			batch, channels = x.shape
			x_input = self.finput(x)
			x_output = self.foutput(x_input)
			return nn.functional.softmax(x_output, dim=1)


def to_categorical(data):
	categories = torch.zeros(data.shape[0])
	categories[data > -0.3] = 1
	categories[data > 0.3] = 2
	return categories.long()

def loss_fn(dist, truth):
	# negative log loss, which approximates the KL-divergence in expectation
	categories = to_categorical(truth)
	xentropy = torch.nn.CrossEntropyLoss()
	loss = xentropy(dist, categories)
	return loss

def stats(dist, truth):
	dist_cat = torch.argmax(dist, dim=1)
	truth_cat = to_categorical(truth)
	accuracy = torch.sum(dist_cat == truth_cat) / torch.numel(truth_cat)
	dist_pos = dist_cat == 2
	truth_pos = truth_cat == 2
	correct = torch.sum(dist_pos & truth_pos)
	precision = correct / torch.sum(dist_pos)
	recall = correct / torch.sum(truth_pos)
	return {"accuracy": accuracy, "precision": precision, "recall": recall}



def create_indicators(prices, window, series=True):
	# prices: batch x time (most recent last)

	data = {}
	input_length = prices.shape[1] - window + 1

	malong = moving_average(prices, window=int(window/2))[:,-input_length:]
	mashort = moving_average(prices, window=int(window/6))[:,-input_length:]
	macd1 = (mashort - malong) / malong
	if not series:
		macd1 = macd1[:,-1]
	data['macd1'] = macd1 * 100

	malong = moving_average(prices, window=int(window))[:,-input_length:]
	mashort = moving_average(prices, window=int(window/3))[:,-input_length:]
	macd2 = (mashort - malong) / malong
	if not series:
		macd2 = macd2[:,-1]
	data['macd2'] = macd2 * 100

	pct = percent_change(prices)[:,-input_length:]
	if not series:
		pct = pct[:,-1]
	data['pct'] = pct * 100

	x = nn.functional.unfold(prices.unsqueeze(1).unsqueeze(3), kernel_size=(window,1)) # batch x channels (1) x dim1 (t) x dim2 (1)
	var = torch.var(x, dim=1)
	if not series:
		var = var[:,-1]
	data['var'] = (var / malong) * 100

	return data


def percent_change(prices):
	return (prices[:,1:] / prices[:,:-1]) - 1


def moving_average(prices, window):
	kernel = torch.ones((1, 1, window), dtype=torch.float64) / window
	ma = torch.nn.functional.conv1d(prices.unsqueeze(1),kernel)[:,0,:]
	return ma