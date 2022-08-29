import {useNavigate} from 'react-router-dom';

export function NavButton(props: { to: string, desc: string, classNames: string, disabled?: boolean }): JSX.Element {
    const nav = useNavigate();

    function handleClick(): void {
        nav(props.to);
    }

    return (
        <button disabled={props.disabled} className={props.classNames}
                onClick={() => handleClick()}>{props.desc}
        </button>
    )
}
