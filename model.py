import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset, DataLoader


class DiscordDataset(Dataset):
    def __init__(self, texts, labels, vocab, tokenizer, label_map):
        self.texts = texts
        self.labels = labels
        self.vocab = vocab
        self.tokenizer = tokenizer
        self.label_map = label_map

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        tokens = self.tokenizer(self.texts[idx])
        indices = [self.vocab.get(t, self.vocab["<unk>"]) for t in tokens]
        label = self.label_map[self.labels[idx]]
        return torch.tensor(indices, dtype=torch.long), torch.tensor(label, dtype=torch.long)
    

def collate_fn(batch):
    texts, labels = zip(*batch)
    texts_padded = pad_sequence(texts, batch_first=True, padding_value=0)
    labels = torch.stack(labels)
    return texts_padded, labels


class SentimentAnalysisLSTM(nn.Module):
    def __init__(
        self, vocab_size,
        embedding_dim,
        hidden_dim,
        output_dim,
        num_layers,
        dropout
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(
            embedding_dim, hidden_dim,
            num_layers=num_layers,
            bidirectional=True,
            dropout=dropout,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_dim * 2, output_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        embedded = self.dropout(self.embedding(x))
        lstm_out, (hidden, cell) = self.lstm(embedded)

        # Concatenate final forward and backward hidden states
        hidden = self.dropout(torch.cat((hidden[-2, :, :], hidden[-1, :, :]), dim=1))

        return self.fc(hidden)
    

def predict_sentiment(model, text, tokenizer, vocab, device, max_length=100):
    """
    Given a text string, return the softmax probability distribution
    over sentiment classes.
    """
    model.eval()  # disable dropout
    
    # 1. Tokenize text (split into tokens, same method as training)
    tokens = tokenizer(text)
    
    # 2. Convert tokens to indices
    indices = [vocab.get(token, vocab.get("<unk>", 0)) for token in tokens]
    
    # 3. Pad or truncate sequence to fixed length
    if len(indices) < max_length:
        indices += [vocab.get("<pad>", 0)] * (max_length - len(indices))
    else:
        indices = indices[:max_length]
    
    # 4. Convert to tensor (batch of 1)
    input_tensor = torch.tensor(indices, dtype=torch.long).unsqueeze(0).to(device)
    
    # 5. Forward pass
    with torch.no_grad():
        logits = model(input_tensor)
        probs = F.softmax(logits, dim=1)
    
    # 6. Return probabilities as list
    return probs.squeeze(0).cpu().tolist()


# Example Usage and Training Loop (simplified)
if __name__ == "__main__":
    # # Hyperparameters
    # vocab_size = 10000  # Example vocabulary size
    # embedding_dim = 100
    # hidden_dim = 256
    # # For binary sentiment classification (positive/negative)
    # output_dim = 1
    # num_layers = 2
    # dropout = 0.5
    # learning_rate = 1e-3
    # num_epochs = 10
    # batch_size = 32

    # # Dummy data for demonstration
    # # In a real scenario, you would load and preprocess your text data
    # # and create DataLoader objects.
    # # [batch_size, sequence_length]
    # dummy_text_data = torch.randint(0, vocab_size, (batch_size, 50))
    # # Random lengths for padding
    # dummy_lengths = torch.randint(10, 50, (batch_size,))
    # dummy_labels = torch.randint(
    #     0, 2, (batch_size,)).float().unsqueeze(1)  # Binary labels

    # # Instantiate the model
    # model = LSTMClassifier(vocab_size, embedding_dim,
    #                        hidden_dim, output_dim, num_layers, dropout)

    # # Define loss function and optimizer
    # # For binary classification with sigmoid in the final layer
    # criterion = nn.BCEWithLogitsLoss()
    # optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # # Training loop
    # for epoch in range(num_epochs):
    #     model.train()
    #     optimizer.zero_grad()

    #     # Forward pass
    #     predictions = model(dummy_text_data, dummy_lengths)

    #     # Calculate loss
    #     loss = criterion(predictions, dummy_labels)

    #     # Backward pass and optimization
    #     loss.backward()
    #     optimizer.step()

    #     print(f"Epoch {epoch+1}/{num_epochs}, Loss: {loss.item():.4f}")

    # print("Training complete.")

    # # Example inference (simplified)
    # model.eval()
    # with torch.no_grad():
    #     test_text = torch.randint(0, vocab_size, (1, 30))
    #     test_lengths = torch.tensor([30])
    #     # Apply sigmoid for probability
    #     test_prediction = torch.sigmoid(model(test_text, test_lengths))
    #     print(f"Test prediction: {test_prediction.item():.4f}")
    ...