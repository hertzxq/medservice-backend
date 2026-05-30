"""
Employees endpoints: CRUD for branch staff.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_superuser
from app.models.user import User
from app.models.employee import Employee
from app.models.branch import Branch
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse

router = APIRouter(prefix="/employees")


@router.get("", response_model=list[EmployeeResponse])
async def get_employees(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of employees for a branch.
    """
    employees = db.query(Employee).filter(Employee.branch_id == branch_id).all()
    return [EmployeeResponse.model_validate(e) for e in employees]


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    branch_id: int,
    employee_in: EmployeeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """
    Create a new employee for a branch.
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    employee = Employee(
        branch_id=branch_id,
        name=employee_in.name,
        active=employee_in.active,
        profiles=employee_in.profiles,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return EmployeeResponse.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """
    Update employee details.
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = employee_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(employee, key, value)

    db.commit()
    db.refresh(employee)
    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """
    Delete an employee.
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.delete(employee)
    db.commit()
    return None
