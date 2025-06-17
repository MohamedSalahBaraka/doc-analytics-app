import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

class MultiLevelClassifier:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.clf1 = MultinomialNB()
        self.clf2 = MultinomialNB()
        self.clf3 = MultinomialNB()
        self.is_trained = False

    def load_training_data(self, path='training_data.json'):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.training_data = json.load(f)
        except FileNotFoundError:
            print(f"[WARN] Training data not found at '{path}'")
            self.training_data = []


    def train(self):
        texts = []
        labels1 = []
        labels2 = []
        labels3 = []

        for item in self.training_data:
            label_parts = item["label"].split(" > ")
            if len(label_parts) != 3:
                continue  # skip malformed label

            texts.append(item["text"])
            labels1.append(label_parts[0])
            labels2.append(label_parts[1])
            labels3.append(label_parts[2])

        X = self.vectorizer.fit_transform(texts)
        self.clf1.fit(X, labels1)
        self.clf2.fit(X, labels2)
        self.clf3.fit(X, labels3)
        self.is_trained = True


    def classify(self, text, as_dict=False):
        if not self.is_trained:
            raise RuntimeError("Classifier is not trained.")
        vect = self.vectorizer.transform([text])
        l1 = self.clf1.predict(vect)[0]
        l2 = self.clf2.predict(vect)[0]
        l3 = self.clf3.predict(vect)[0]

        if as_dict:
            return {"level1": l1, "level2": l2, "level3": l3}
        return f"{l1} > {l2} > {l3}"

