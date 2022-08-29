export enum MaybeLoadType {
    Waiting = 'maybe-load-type__waiting',
    Uninitialised = 'maybe-load-type__uninitialised',
    Loaded = 'maybe-load-type__loaded',
    NotFound = 'maybe-load-type__not_found',
}

export interface Loaded<T> {
    type: typeof MaybeLoadType.Loaded
    value: T
}

export interface NotFound {
    type: typeof MaybeLoadType.NotFound
}

export interface Waiting {
    type: typeof MaybeLoadType.Waiting
    iat: number
}

export interface Uninitialised {
    type: typeof MaybeLoadType.Uninitialised
}

export type MaybeLoad<T>
    = Loaded<T>
    | NotFound
    | Waiting
    | Uninitialised

export const notFound = (): NotFound => ({
    type: MaybeLoadType.NotFound,
})

export const loaded = <T, >(value: T): Loaded<T> => ({
    type: MaybeLoadType.Loaded,
    value,
})

export const waiting = (): Waiting => ({
    type: MaybeLoadType.Waiting,
    iat: new Date().getTime()
})

export const uninitialised = (): Uninitialised => ({
    type: MaybeLoadType.Uninitialised
})