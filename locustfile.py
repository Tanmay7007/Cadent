from locust import HttpUser, task, between, LoadTestShape


class MyUser(HttpUser):
    # Users wait 1-2 seconds between clicks to simulate realistic browsing
    wait_time = between(1, 2)

    @task
    def access_home(self):
        # Hits the default page of your Load Balancer
        self.client.get("/")


class MLDataShape(LoadTestShape):
    # Format: {"duration": seconds_from_start, "users": target_active_users, "spawn_rate": users_added_per_sec}

    stages = [
        # State 1: The Baseline (Mins 0-3)
        {"duration": 180, "users": 250, "spawn_rate": 10},

        # State 2: The Safe Viral Event (Mins 3-6)
        {"duration": 360, "users": 1000, "spawn_rate": 50},

        # State 3: The Insider Threat (Mins 6-9)
        {"duration": 540, "users": 500, "spawn_rate": 100},

        # State 4: The Total Meltdown (Mins 9-12)
        {"duration": 720, "users": 1000, "spawn_rate": 50},

        # State 5: The Cooldown (Mins 12-15)
        {"duration": 900, "users": 100, "spawn_rate": 100},

        # State 6: Final Blow (15-20)
        {"duration":1080, "users":750, "spawn_rate": 100},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None