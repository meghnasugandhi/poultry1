from app.services.calculator_service import CALCULATORS

from fastapi import APIRouter

from app.schemas.assistant import CalculatorRequest, CalculatorResponse

router = APIRouter(prefix="/calculator", tags=["Poultry Calculator"])


@router.get("/types")
async def list_calculations():
    return [
        {"type": key, "name": calc["name"], "inputs": calc["inputs"]}
        for key, calc in CALCULATORS.items()
    ]


@router.post("/calculate", response_model=CalculatorResponse)
async def calculate(data: CalculatorRequest):
    calc = CALCULATORS.get(data.calculation_type)
    if not calc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"Unknown calculation: {data.calculation_type}")

    result = calc["fn"](data.inputs)
    return CalculatorResponse(
        calculation_type=data.calculation_type,
        formula=calc["formula"],
        steps=result["steps"],
        result=result["value"],
        explanation=result["explanation"],
    )
