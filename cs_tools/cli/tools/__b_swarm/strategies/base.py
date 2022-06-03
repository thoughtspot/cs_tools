from locust import User, between


class ThoughtSpotUser(User):
    wait_time = between(1, 5)

    def __init__(self, environment):
        super().__init__(environment)
        self.ts = environment.thoughtspot
        self.client = self.ts.api._http
