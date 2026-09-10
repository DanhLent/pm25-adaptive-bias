// AMBA APB3 wrapper for the bus-independent PM2.5 alert core.
// PROCESS is independent of SAMPLE_VALID so invalid samples still complete.
module pm25_apb_wrapper #(
    parameter integer ALPHA_SHIFT = 3,
    parameter integer PADDR_WIDTH = 8
) (
    input wire PCLK,
    input wire PRESETn,
    input wire PSEL,
    input wire PENABLE,
    input wire PWRITE,
    input wire [PADDR_WIDTH-1:0] PADDR,
    input wire [31:0] PWDATA,
    output reg [31:0] PRDATA,
    output wire PREADY,
    output reg PSLVERR
);

localparam [PADDR_WIDTH-1:0] ADDR_IP_ID           = 8'h00;
localparam [PADDR_WIDTH-1:0] ADDR_VERSION         = 8'h04;
localparam [PADDR_WIDTH-1:0] ADDR_CONTROL         = 8'h08;
localparam [PADDR_WIDTH-1:0] ADDR_CAMS_PM25_X16  = 8'h0C;
localparam [PADDR_WIDTH-1:0] ADDR_PA_PM25_X16    = 8'h10;
localparam [PADDR_WIDTH-1:0] ADDR_HOUR            = 8'h14;
localparam [PADDR_WIDTH-1:0] ADDR_STATUS          = 8'h18;
localparam [PADDR_WIDTH-1:0] ADDR_RESULT_X16      = 8'h1C;
localparam [PADDR_WIDTH-1:0] ADDR_BIAS_STATE_X16 = 8'h20;
localparam [PADDR_WIDTH-1:0] ADDR_CONFIG          = 8'h24;

wire apb_access;
wire address_aligned;
wire mapped_address;
wire read_only_address;
wire process_write;

reg payload_sample_valid;
reg payload_qc_ok;
reg signed [31:0] cams_pm25_x16_reg;
reg signed [31:0] pa_pm25_x16_reg;
reg [4:0] hour_reg;

reg snapshot_sample_valid;
reg snapshot_qc_ok;
reg signed [31:0] snapshot_cams_pm25_x16;
reg signed [31:0] snapshot_pa_pm25_x16;
reg [4:0] snapshot_hour;

reg core_request_pulse;
reg response_capture_pending;
reg busy;
reg done;
reg status_result_valid;
reg status_accepted;
reg status_alert_state;
reg [2:0] status_alert_level;
reg signed [31:0] result_pm25_x16;
reg signed [31:0] result_bias_state_x16;

wire core_sample_ready;
wire core_result_valid;
wire core_accepted;
wire signed [31:0] core_fused_pm25_x16;
wire [2:0] core_alert_level;
wire core_alert_state_after;
wire signed [31:0] core_bias_state_x16;

assign PREADY = 1'b1;
assign apb_access = PSEL && PENABLE;
assign address_aligned = (PADDR[1:0] == 2'b00);
assign mapped_address =
       (PADDR == ADDR_IP_ID)
    || (PADDR == ADDR_VERSION)
    || (PADDR == ADDR_CONTROL)
    || (PADDR == ADDR_CAMS_PM25_X16)
    || (PADDR == ADDR_PA_PM25_X16)
    || (PADDR == ADDR_HOUR)
    || (PADDR == ADDR_STATUS)
    || (PADDR == ADDR_RESULT_X16)
    || (PADDR == ADDR_BIAS_STATE_X16)
    || (PADDR == ADDR_CONFIG);
assign read_only_address =
       (PADDR == ADDR_IP_ID)
    || (PADDR == ADDR_VERSION)
    || (PADDR == ADDR_STATUS)
    || (PADDR == ADDR_RESULT_X16)
    || (PADDR == ADDR_BIAS_STATE_X16)
    || (PADDR == ADDR_CONFIG);
assign process_write = apb_access && PWRITE
                     && (PADDR == ADDR_CONTROL) && PWDATA[0];

always @* begin
    PRDATA = 32'd0;
    case (PADDR)
        ADDR_IP_ID:           PRDATA = 32'h504D3235;
        ADDR_VERSION:         PRDATA = 32'h00010000;
        ADDR_CONTROL:         PRDATA = {29'd0, payload_qc_ok,
                                        payload_sample_valid, 1'b0};
        ADDR_CAMS_PM25_X16:   PRDATA = cams_pm25_x16_reg;
        ADDR_PA_PM25_X16:     PRDATA = pa_pm25_x16_reg;
        ADDR_HOUR:            PRDATA = {27'd0, hour_reg};
        ADDR_STATUS:          PRDATA = {24'd0, status_alert_level,
                                        status_alert_state, status_accepted,
                                        status_result_valid, done, busy};
        ADDR_RESULT_X16:      PRDATA = result_pm25_x16;
        ADDR_BIAS_STATE_X16:  PRDATA = result_bias_state_x16;
        ADDR_CONFIG:          PRDATA = {16'd0, 8'd16, ALPHA_SHIFT[7:0]};
        default:              PRDATA = 32'd0;
    endcase
end

always @* begin
    PSLVERR = 1'b0;
    if (apb_access) begin
        if (!address_aligned || !mapped_address) begin
            PSLVERR = 1'b1;
        end else if (PWRITE && read_only_address) begin
            PSLVERR = 1'b1;
        end else if (process_write && busy) begin
            PSLVERR = 1'b1;
        end
    end
end

pm25_alert_core #(
    .ALPHA_SHIFT(ALPHA_SHIFT)
) u_core (
    .clk(PCLK),
    .rst_n(PRESETn),
    .sample_valid(core_request_pulse && snapshot_sample_valid),
    .qc_ok(snapshot_qc_ok),
    .hour(snapshot_hour),
    .cams_pm25_x16(snapshot_cams_pm25_x16),
    .pa_pm25_x16(snapshot_pa_pm25_x16),
    .sample_ready(core_sample_ready),
    .result_valid(core_result_valid),
    .accepted(core_accepted),
    .hour_out(),
    .bias_before_x16(),
    .residual_x16(),
    .error_x16(),
    .delta_x16(),
    .bias_after_x16(),
    .fused_raw_x16(),
    .fused_pm25_x16(core_fused_pm25_x16),
    .alert_level(core_alert_level),
    .alert_state_before(),
    .alert_state_after(core_alert_state_after),
    .bias_state_x16(core_bias_state_x16)
);

always @(posedge PCLK or negedge PRESETn) begin
    if (!PRESETn) begin
        payload_sample_valid <= 1'b0;
        payload_qc_ok <= 1'b0;
        cams_pm25_x16_reg <= 32'sd0;
        pa_pm25_x16_reg <= 32'sd0;
        hour_reg <= 5'd0;
        snapshot_sample_valid <= 1'b0;
        snapshot_qc_ok <= 1'b0;
        snapshot_cams_pm25_x16 <= 32'sd0;
        snapshot_pa_pm25_x16 <= 32'sd0;
        snapshot_hour <= 5'd0;
        core_request_pulse <= 1'b0;
        response_capture_pending <= 1'b0;
        busy <= 1'b0;
        done <= 1'b0;
        status_result_valid <= 1'b0;
        status_accepted <= 1'b0;
        status_alert_state <= 1'b0;
        status_alert_level <= 3'd0;
        result_pm25_x16 <= 32'sd0;
        result_bias_state_x16 <= 32'sd0;
    end else begin
        core_request_pulse <= 1'b0;

        if (core_request_pulse) begin
            response_capture_pending <= 1'b1;
        end

        if (response_capture_pending) begin
            status_result_valid <= core_result_valid;
            status_accepted <= core_accepted;
            status_alert_state <= core_alert_state_after;
            status_alert_level <= core_alert_level;
            result_pm25_x16 <= core_fused_pm25_x16;
            result_bias_state_x16 <= core_bias_state_x16;
            response_capture_pending <= 1'b0;
            busy <= 1'b0;
            done <= 1'b1;
        end

        if (apb_access && PWRITE && !PSLVERR) begin
            case (PADDR)
                ADDR_CONTROL: begin
                    payload_sample_valid <= PWDATA[1];
                    payload_qc_ok <= PWDATA[2];
                    if (PWDATA[0]) begin
                        snapshot_sample_valid <= PWDATA[1];
                        snapshot_qc_ok <= PWDATA[2];
                        snapshot_cams_pm25_x16 <= cams_pm25_x16_reg;
                        snapshot_pa_pm25_x16 <= pa_pm25_x16_reg;
                        snapshot_hour <= hour_reg;
                        core_request_pulse <= 1'b1;
                        busy <= 1'b1;
                        done <= 1'b0;
                    end
                end
                ADDR_CAMS_PM25_X16: cams_pm25_x16_reg <= PWDATA;
                ADDR_PA_PM25_X16:   pa_pm25_x16_reg <= PWDATA;
                ADDR_HOUR:          hour_reg <= PWDATA[4:0];
                default: begin end
            endcase
        end
    end
end

endmodule
