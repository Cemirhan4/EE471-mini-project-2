# Custom Exceptions
class ItemNotFoundError(Exception):
    """Raised when an item with the given ID does not exist in the collection."""
    pass

class ItemStateError(Exception):
    """Raised when a checkout or return action is invalid given the item's current state."""
    pass

# Base Class
class MediaItem:
    """
    Represents a generic item in a library collection.
    Base class providing core checkout and return functionality.
    """
    def __init__(self, title, author, is_available=True):
        self.id = None
        self.title = title
        self.author = author
        self.is_available = is_available

    def checkout(self):
        if self.is_available:
            self.is_available = False
            return "Successful checkout"
        else:
            raise ItemStateError(f"'{self.title}' is already checked out.")

    def return_item(self):
        if self.is_available:
            raise ItemStateError(f"'{self.title}' is not currently checked out.")
        self.is_available = True
        return "Item returned successfully."

    def to_dict(self):
        return {
            "id": self.id,
            "type": type(self).__name__,
            "title": self.title,
            "author": self.author,
            "is_available": self.is_available,
        }

    def __str__(self):
        status = "Available" if self.is_available else "Checked Out"
        return f"{self.title} by {self.author} [{status}]"


class Book(MediaItem):
    def __init__(self, title, author, page_count, is_available=True):
        super().__init__(title, author, is_available)
        self.page_count = page_count

    def to_dict(self):
        data = super().to_dict()
        data["page_count"] = self.page_count
        return data

    def __str__(self):
        status = "Available" if self.is_available else "Checked Out"
        return f"{self.title} by {self.author} [{status}] - {self.page_count} pages"


class DVD(MediaItem):
    def __init__(self, title, author, duration, is_available=True):
        super().__init__(title, author, is_available)
        self.duration = duration

    def checkout(self):
        result = super().checkout()
        return f"{result} — Handle with care: Do not scratch the disc."

    def to_dict(self):
        data = super().to_dict()
        data["duration"] = self.duration
        return data

    def __str__(self):
        status = "Available" if self.is_available else "Checked Out"
        return f"{self.title} by {self.author} [{status}] - {self.duration} mins"


class LibraryCollection:
    def __init__(self):
        self.items = []
        self._next_id = 1

    def add_item(self, item):
        item.id = self._next_id
        self._next_id += 1
        self.items.append(item)
        return item.id

    def get_item(self, item_id):
        for item in self.items:
            if item.id == item_id:
                return item
        raise ItemNotFoundError(f"Item with ID {item_id} not found.")

    def update_item(self, item_id, **kwargs):
        item = self.get_item(item_id)
        for key, value in kwargs.items():
            if key in ('title', 'author'):
                setattr(item, key, value)
            elif key == 'page_count' and isinstance(item, Book):
                item.page_count = value
            elif key == 'duration' and isinstance(item, DVD):
                item.duration = value
        return item

    def remove_item(self, item_id):
        item = self.get_item(item_id)
        if not item.is_available:
            raise ItemStateError(f"Cannot remove '{item.title}' because it is currently checked out.")
        self.items.remove(item)

    def list_items(self, available=None, item_type=None):
        results = self.items
        if available is not None:
            results = [i for i in results if i.is_available == available]
        if item_type is not None:
            results = [i for i in results if isinstance(i, item_type)]
        return results
