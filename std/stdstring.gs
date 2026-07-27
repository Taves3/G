template <T>
def string stringify(T object) {
    return object.__string__()
}