import React from 'react';
import board from '../images/Tic-Tac-Toe.svg';
import { GoogleLogin } from '@react-oauth/google';
import { NavButton } from '../common/common';
import '../styles.css';
import { MaybeType } from '../common/types/maybe';
import PageTemplate from '../common/pageTemplate';
import { MaybeLoadType } from '../common/types/load';


class SignInChoices extends PageTemplate {

    render(): JSX.Element {
        return (
            <div>
                {
                    this.state.currentUser.type === MaybeLoadType.Loaded ?
                        <div className='buttons'>
                            <NavButton to="/pools" desc="Create Pool" classNames='selected' />
                        </div>
                        : <GoogleLogin
                            onSuccess={credentialResponse => { this.handleCallBackResponse(credentialResponse) }}
                            onError={() => {
                                console.log('Login Failed');
                            }}
                            useOneTap
                        />
                }
            </div>
        )
    }
}


class Login extends React.Component {
    render(): JSX.Element {
        return (
            <div className='Login'>
                <div className='header'>
                    <b>Tic Tac Toe Fighters</b>
                </div>
                <div className='content'>
                    <img className='image' src={board} alt='board' />
                    <SignInChoices />
                    <img className='image' src={board} alt='board' />
                </div>
            </div>
        );
    }
}

export default Login;
