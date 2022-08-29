import React from 'react';
import PageTemplate from '../common/pageTemplate';
import User from '../components/User';
import jwtDecode from 'jwt-decode';
import { CredentialResponse, GoogleLogin } from '@react-oauth/google';
import { MaybeLoad, MaybeLoadType } from '../common/types/load';

type NavButtonProps = {
    name: string
    link: string
}

const BUTTONS: NavButtonProps[] = [
    { "name": "Tic Tac Toe Fighters", "link": "/" },
    { "name": "Pools", "link": "/pools" }
]


class NavUserInfo extends React.Component<User> {
    render() {
        return (
            <div className="NavUserInfo">
                <img src={this.props.image} alt="Profile" referrerPolicy='no-referrer'></img>
                <p>{this.props.name}</p>
            </div>
        )
    }
}

class NavGuest extends React.Component<{response: (credentialResponse: CredentialResponse) => void}> {
    render() {
        return (
            <div className="NavGuest">
                <GoogleLogin
                    onSuccess={this.props.response}
                    onError={() => {
                        console.log('Login Failed');
                    }}
                    useOneTap
                />
            </div>

        )
    }
}

type NavUserProps = {
    session_id: MaybeLoad<string>
    callbackFunc: (credentialResponse: CredentialResponse) => void
}

class NavUser extends React.Component<NavUserProps> {
    render(): JSX.Element {
        var currentProps: JSX.Element = <div />

        switch (this.props.session_id.type) {
            case MaybeLoadType.Loaded:
                const currentUser = jwtDecode<User>(this.props.session_id.value)
                console.log("Current user", currentUser)
                currentProps = <NavUserInfo {...currentUser} />
                break;
        
            case MaybeLoadType.Waiting:
                currentProps = <div />
                break;
            default:
                currentProps = <NavGuest response={this.props.callbackFunc}/>
                break;
        }

        return (
            <div className="NavUser">
                {currentProps}
            </div>
        )
    }

}

class NavButton extends React.Component<NavButtonProps> {
    render(): JSX.Element {
        return (
            <a className="button" href={this.props.link}>{this.props.name}</a>
        )
    }
}

class NavButtonList extends React.Component<{ buttonProps: NavButtonProps[] }> {
    render(): JSX.Element {
        const buttons: JSX.Element[] = []

        this.props.buttonProps.forEach((button, index) => {
            buttons.push(
                <NavButton key={index} {...button} />
            )
        })
        return (
            <div className="NavButtonList">
                {buttons}
            </div>
        )
    }
}

class Navbar extends PageTemplate {

    render(): JSX.Element {

        this.handleCallBackResponse = this.handleCallBackResponse.bind(this)

        return (
            <div className="Navbar">
                <NavButtonList buttonProps={BUTTONS} />
                <NavUser session_id={this.state.currentUser} callbackFunc={this.handleCallBackResponse} />
            </div>
        )
    }
}

export default Navbar;
