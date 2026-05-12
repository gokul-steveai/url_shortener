import string


class ShortenerService:

    ALPHABET = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    BASE = len(ALPHABET)

    @classmethod
    def encode(cls, number: int) -> str:
        """
        Convert a number to a base-62 string
        """
        if number < 0:
            raise ValueError("Number must be non-negative")

        if number == 0:
            return cls.ALPHABET[0]

        arr = []
        while number:
            number, rem = divmod(number, cls.BASE)
            arr.append(cls.ALPHABET[rem])

        arr.reverse()
        return "".join(arr)

    @classmethod
    def decode(cls, string_id: str) -> int:
        """
        Convert a base-62 string to a number
        """
        number = 0
        for char in string_id:
            number = number * cls.BASE + cls.ALPHABET.index(char)
        return number
