# Middleware Check Precedence

Understanding the order in which the `MaintenanceModeMiddleware` checks for various conditions is key to predicting its behavior, especially when combining features like route-specific decorators, exemptions, and the global maintenance override context.

The middleware evaluates conditions in a specific sequence to determine whether to return a maintenance response or allow the request to proceed. Here is the order of precedence:

1.  **Route Forced ON**:
    - **Behavior**: If a route is decorated with `@force_maintenance_mode_on`, the middleware immediately returns a maintenance response.
    - **Why**: This is the most absolute "block" directive. It overrides all other conditions, ensuring that specific paths are always in maintenance if marked as such.

2.  **Route Forced OFF**:
    - **Behavior**: If a route is decorated with `@force_maintenance_mode_off`, the middleware immediately allows the request to proceed.
    - **Why**: This is the most absolute "allow" directive for a specific path. It bypasses general maintenance mode and the override context for this route.

3.  **Request Exempt**:
    - **Behavior**: If the request meets the criteria defined in your `exempt_handler` (if provided), the middleware allows the request to proceed.
    - **Why**: Exemptions are powerful and are intended to bypass general maintenance states. An exempt request will proceed unless its path was explicitly forced ON (see point 1).

4.  **Maintenance Mode Override Context**:
    - **Behavior**: If the `maintenance_mode_on()` context manager is active, the middleware returns a maintenance response.
    - **Why**: This allows for temporary, global activation of maintenance mode. It applies if the request wasn't already allowed by a `@force_maintenance_mode_off` or an exemption.

5.  **Global Active Maintenance Mode**:
    - **Behavior**: If maintenance mode is active by either being explicitly enabled or based on the configured backend (e.g., environment variable or file), the middleware returns a maintenance response.
    - **Why**: This is the standard, global maintenance check. It applies if no prior, more specific rule (like path-specific forcing, exemptions, or an active override context) has already handled the request.

6.  **Default Action**:
    - **Behavior**: If none of the above conditions result in a maintenance response, the request proceeds to the next handler in the application.

This order ensures that the most specific rules (like forcing a path on or off) take precedence, followed by general exemptions, and then broader states like the override context and the standard maintenance mode. This layered approach provides both flexibility and predictable behavior.
