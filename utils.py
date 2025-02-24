def pad_number(unpadded, length) -> str:
    unpadded = str(unpadded)
    assert 0 < len(unpadded) <= length

    if len(unpadded) == length:
        return unpadded

    leading_zero_count = length - len(unpadded)
    print(unpadded, leading_zero_count)

    return (("0" * leading_zero_count) + unpadded)
