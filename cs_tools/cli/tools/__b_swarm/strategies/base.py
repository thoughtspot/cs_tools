# from locust import User, between


# class ThoughtSpotUser(User):
#     wait_time = between(1, 5)

#     def __init__(self, environment):
#         super().__init__(environment)
#         self.ts = environment.thoughtspot
#         self.client = self.ts.api._http

#
# - needs to be repeatable, export all the searches
# - integrate with syncers?
#

# STRATEGIES:
#
# - data validity check (pre/post export as json); git diff --no-index
# - test answers/liveboards (all, guids, tags, random)
# - scalability testing
# 
