export enum MaybeType {
    Just = 'maybe-type__just',
    Nothing = 'maybe-type__nothing',
}

export interface Just<T> {
    type: typeof MaybeType.Just
    value: T
}

export interface Nothing {
    type: typeof MaybeType.Nothing
}

export type Maybe<T>
    = Just<T>
    | Nothing

export const nothing = (): Nothing => ({
    type: MaybeType.Nothing,
})

export const just = <T, >(value: T): Just<T> => ({
    type: MaybeType.Just,
    value,
})

type Empty = undefined | null;

export function maybeOf<T, >(value: T | Empty): Maybe<T> {
    return value === undefined || value === null
        ? nothing()
        : just(value)
}

export function MaybeMap<A, B>(f: (val: A) => B, m: Maybe<A>): Maybe<B> {
    switch (m.type) {
        case MaybeType.Nothing:
            return nothing()
        case MaybeType.Just:
            return just(f(m.value))
    }
}
