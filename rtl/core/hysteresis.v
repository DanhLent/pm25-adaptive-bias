// Combinational binary alert-hysteresis update.
// Invalid samples hold the previous state.
module hysteresis (
    input prev_alert_state,
    input sample_valid,
    input signed [31:0] fused_pm25_x16,
    output reg next_alert_state
);

`include "pm25_constants.vh"

always @* begin
    next_alert_state = prev_alert_state;

    if (sample_valid) begin
        if (!prev_alert_state && (fused_pm25_x16 >= ALERT_ON_X16)) begin
            next_alert_state = 1'b1;
        end else if (prev_alert_state && (fused_pm25_x16 <= ALERT_OFF_X16)) begin
            next_alert_state = 1'b0;
        end
    end
end

endmodule
