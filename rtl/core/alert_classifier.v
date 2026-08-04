// Combinational alert classifier for saturated x16 PM2.5 values.
module alert_classifier (
    input signed [31:0] fused_pm25_x16,
    output reg [2:0] alert_level
);

`include "pm25_constants.vh"

always @* begin
    if (fused_pm25_x16 <= GOOD_MAX_X16) begin
        alert_level = 3'd0;
    end else if (fused_pm25_x16 <= MODERATE_MAX_X16) begin
        alert_level = 3'd1;
    end else if (fused_pm25_x16 <= USG_MAX_X16) begin
        alert_level = 3'd2;
    end else if (fused_pm25_x16 <= UNHEALTHY_MAX_X16) begin
        alert_level = 3'd3;
    end else begin
        alert_level = 3'd4;
    end
end

endmodule
