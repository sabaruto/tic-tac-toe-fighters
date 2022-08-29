import React from "react";
import User from "../components/User";
import { Cookies } from "react-cookie";
import { CredentialResponse } from "@react-oauth/google";
import axios from "axios";
import jwtDecode from "jwt-decode";
import { MaybeLoad, loaded, notFound, uninitialised, waiting } from "./types/load";

const cookies = new Cookies();

class PageTemplate extends React.Component {
    state: {
        currentUser: MaybeLoad<string>
    } = {
            currentUser: uninitialised()
        }

    handleCallBackResponse(response: CredentialResponse): void {
        this.setState({ currentUser: waiting() })
        axios.post('/api/login/', {
            google_jwt: response.credential
        })
            .then((res) => {
                const session_id = res.data['session_token'] as string
                const user_info = jwtDecode<User>(session_id) as any

                cookies.set('session_id', session_id, {
                    expires: new Date(user_info.exp * 1000),
                    path: "/",
                    sameSite: 'lax'
                })
                window.location.reload();
            })
            .catch((err) => {
                console.log(err)
                this.setState({ currentUser: notFound() })
            })
    }

    updateCurrentUser() {
        if (cookies.get('session_id')) {
            const session_token = cookies.get('session_id') as string
            console.log("Found token: ", session_token)

            this.setState({ currentUser: waiting() })

            axios.get('/api/login/', {
                withCredentials: true
            })
                .then((res) => {
                    if (res.status === 200) {
                        console.log("Found valid login token in cookies")
                        this.setState({ currentUser: loaded<string>(cookies.get('session_id')) })
                    } else {
                        console.log("Current token isn't valid")
                        cookies.remove('session_id')
                        this.setState({ currentUser: notFound() })
                    }
                })
                .catch((err) => {
                    console.log(err)
                    this.setState({ currentUser: notFound() })
                })
        } else {
            this.setState({ currentUser: notFound() })
        }
    }

    componentDidMount(): void {
        this.updateCurrentUser()
    }
}

export default PageTemplate