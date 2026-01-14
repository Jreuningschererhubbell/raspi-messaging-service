class ServiceMessenger:
    def __init__(self, device_name: str):
        self.device_name = device_name
        self.service_name = None

    def post_message(self, message) -> bool:
        raise NotImplementedError("Subclasses must implement this method.")
        pass



class ServiceMessengerGroup:
    def __init__(self):
        self.messengers = []

    def add_messenger(self, messenger: ServiceMessenger) -> None:
        self.messengers.append(messenger)

    def post_message(self, message) -> dict[str, bool]:
        results = {}
        for messenger in self.messengers:
            result = messenger.post_message(message)
            results[messenger.service_name] = result
        return results
