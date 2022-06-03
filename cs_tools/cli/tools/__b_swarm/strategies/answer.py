import time

from locust import task, between

from .base import ThoughtSpotUser


class AnswerUser(ThoughtSpotUser):
    wait_time = between(1, 5)

    # def on_start(self):
    #     self.client.post('/login', json={'username': 'foo', 'password': 'bar'})

    # @task
    # def hello_world(self):
    #     self.client.get('/hello')
    #     self.client.get('/world')
