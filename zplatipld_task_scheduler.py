import threading
import schedule
import time
from flask_socketio import SocketIO

global do_running

class IPLDScheduler:
    def __init__(self) -> None:
        self.schedule_tasks = []

    def task_to_execute(self, task_id):
        print(f"Task testing {task_id}")

    def schedule_task(self, schedule_time, task_id, day_of_week=None):
        if day_of_week == "sunday":
            job = (
                schedule.every()
                .sunday.at(schedule_time)
                .do(self.task_to_execute, task_id=task_id)
            )
            self.schedule_tasks.append(job)
        elif day_of_week == "monday":
            job = (
                schedule.every()
                .monday.at(schedule_time)
                .do(self.task_to_execute, task_id=task_id)
            )
            self.schedule_tasks.append(job)
        elif day_of_week == "tuesday":
            job = (
                schedule.every()
                .tuesday.at(schedule_time)
                .do(self.task_to_execute, task_id=task_id)
            )
            self.schedule_tasks.append(job)
        elif day_of_week == "wednesday":
            job = (
                schedule.every()
                .wednesday.at(schedule_time)
                .do(self.task_to_execute, task_id=task_id)
            )
            self.schedule_tasks.append(job)
        elif day_of_week == "thursday":
            job = (
                schedule.every()
                .thursday.at(schedule_time)
                .do(self.task_to_execute, task_id=task_id)
            )
            self.schedule_tasks.append(job)
        elif day_of_week == "friday":
            job = (
                schedule.every()
                .friday.at(schedule_time)
                .do(self.task_to_execute, task_id=task_id)
            )
            self.schedule_tasks.append(job)
        elif day_of_week == "saturday":
            job = (
                schedule.every()
                .saturday.at(schedule_time)
                .do(self.task_to_execute, task_id=task_id)
            )
            self.schedule_tasks.append(job)

    def cancel_all_tasks(self):
        for task in self.schedule_tasks:
            task.unregister()
        self.schedule_tasks.clear()

    def schedule_monitor(self):
        return schedule.get_jobs()

    def run(self):
        global do_running
        while not do_running:
            schedule.run_pending()
            socketio.emit(
            "task_progress",
            {
                "result": lpares_dic,
                "percent": percent_of_progress,
                "error": send_error,
            },
        )
            print(scheduler.schedule_monitor())
            time.sleep(1)

    def backgroud_run(action):
        thread_load = threading.Thread(
            scheduler.run()
        )
        if action == "start":
            thread_load.start()
            do_running = True
        elif action == "stop":
            do_running = False
            thread_load.join()


if __name__ == "__main__":
    scheduler = IPLDScheduler()

    scheduler.schedule_task("16:09:00", 1, day_of_week="monday")
    scheduler.run()
