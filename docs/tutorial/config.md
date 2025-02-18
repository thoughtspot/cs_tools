---
hide:
    - toc
---

# Configuration Files

__CS Tools__ is built on top of the __ThoughtSpot__ [REST APIs][ts-rest-apis].

In order to interact with __ThoughtSpot__ you must be signed in, this is known as having an "active session".

When you create a configuration, you define the User to log in as, so the level of privilege you gain depends on who
that User is.

!!! info "Authentications methods that __CS Tools__ supports"
    CS Tools supports 3 main methods of establishing a session with ThoughtSpot, all of which can be used together.

    === "Basic"
        This is your standard combination of __username__{ .fc-purple } and __password__{ .fc-purple }.

        - [Basic Authentication][ts-rest-auth-basic]

        :rotating_light: Your password is not held in cleartext.

    === "Trusted"
        This is a global password which allows you to log in as any user you choose. You can find the __Secret
        Key__{ .fc-purple } in the __Developer tab__ under __Security Settings__.

        - [Trusted Authentication][ts-rest-auth-trusted]

        :superhero: Only Administrators can see the Trusted Authentication secret key.

    === "Bearer Token"
        This is a user-local password placement with a designated lifetime. Call the API with your password (or secret
        key) to receieve a __bearer token__{ .fc-purple }.

        - [Bearer Token Authentication][ts-rest-auth-bearer-token]

        :clock11: This token will expire after the `validitiy_time_in_sec`.


~cs~tools config create --help

## Exploring the Tools

With a configuration file set up, we're ready to explore all the utilities that come with __CS Tools__.

__In the next section__, we'll learn about the __Archiver__{ .fc-purple } tool and see how we can leverage it to keep
our __ThoughtSpot__ cluster clean while it grows.

[ts-rest-apis]: https://developers.thoughtspot.com/docs/?pageid=rest-apis
[ts-rest-auth-basic]: https://developers.thoughtspot.com/docs/embed-auth#basic-auth-embed
[ts-rest-auth-trusted]: https://developers.thoughtspot.com/docs/trusted-auth-secret-key
[ts-rest-auth-bearer-token]: https://developers.thoughtspot.com/docs/api-authv2#bearerToken