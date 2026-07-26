template <T>
struct ListIterator {
    List list
    int index

    def void constructor(List list) {
        this.list = list
        this.index = 0
    }

    def bool __has_next__() {
        return index < list.length
    }

    def T __next__() {
        this.index = index + 1
        return get_attribute(list, stringify(index))
    }
}

template <T>
struct List {
    int length

    def void constructor() {
        this.length = 0
    }
    
    def void add(T element) {
        set_attribute(this, stringify(length), element)
    }

    def ListIterator __iterate__() {
        return ListIterator(this)
    }

    def int __length__() {
        return this.length
    }
}